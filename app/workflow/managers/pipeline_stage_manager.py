"""
Pipeline Stage Manager

Manages pipeline stages with pluggable architecture, dependencies,
and dynamic stage addition/removal.
"""

import threading
import logging
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class StageState(Enum):
    """Pipeline stage states."""
    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class StageConfig:
    """Configuration for a pipeline stage."""
    name: str
    enabled: bool = True
    required: bool = True
    timeout: float = 5.0
    retry_on_error: bool = True
    max_retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StageResult:
    """Result from stage execution."""
    stage_name: str
    success: bool
    data: Any = None
    error: Optional[Exception] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class PipelineStage:
    """
    Base class for pipeline stages.
    
    Stages are pluggable components that process data in sequence.
    """
    
    def __init__(self, config: StageConfig):
        """
        Initialize pipeline stage.
        
        Args:
            config: Stage configuration
        """
        self.config = config
        self.state = StageState.IDLE
        self.logger = logging.getLogger(f"{__name__}.{config.name}")
        
        # Statistics
        self.executions = 0
        self.successes = 0
        self.failures = 0
        self.total_time = 0.0
        
        self.lock = threading.RLock()
    
    def execute(self, input_data: Any) -> StageResult:
        """
        Execute the stage.
        
        Args:
            input_data: Input data for stage
            
        Returns:
            StageResult: Execution result
        """
        if not self.config.enabled:
            return StageResult(
                stage_name=self.config.name,
                success=True,
                data=input_data,  # Pass through
                execution_time=0.0
            )
        
        start_time = datetime.now()
        
        try:
            self.state = StageState.RUNNING
            
            # Process data
            output_data = self.process(input_data)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            with self.lock:
                self.executions += 1
                self.successes += 1
                self.total_time += execution_time
            
            self.state = StageState.READY
            
            return StageResult(
                stage_name=self.config.name,
                success=True,
                data=output_data,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            with self.lock:
                self.executions += 1
                self.failures += 1
                self.total_time += execution_time
            
            self.state = StageState.ERROR
            self.logger.error(f"Stage {self.config.name} failed: {e}")
            
            return StageResult(
                stage_name=self.config.name,
                success=False,
                error=e,
                execution_time=execution_time
            )
    
    def process(self, input_data: Any) -> Any:
        """
        Process data (override in subclass).
        
        Args:
            input_data: Input data
            
        Returns:
            Processed data
        """
        raise NotImplementedError("Subclass must implement process()")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get stage statistics."""
        with self.lock:
            avg_time = self.total_time / self.executions if self.executions > 0 else 0
            success_rate = self.successes / self.executions * 100 if self.executions > 0 else 0
            
            return {
                'name': self.config.name,
                'state': self.state.value,
                'enabled': self.config.enabled,
                'executions': self.executions,
                'successes': self.successes,
                'failures': self.failures,
                'success_rate': success_rate,
                'average_time': avg_time,
                'total_time': self.total_time
            }


class PipelineStageManager:
    """
    Manages pipeline stages with dependencies and dynamic configuration.
    
    Features:
    - Stage registration and execution
    - Dependency resolution
    - Dynamic stage addition/removal
    - Stage health monitoring
    - Execution order optimization
    """
    
    def __init__(self):
        """Initialize stage manager."""
        self.logger = logging.getLogger(__name__)
        
        # Registered stages
        self.stages: Dict[str, PipelineStage] = {}
        self.stage_order: List[str] = []
        
        # Execution control
        self.lock = threading.RLock()
        
        # Callbacks
        self.pre_stage_callbacks: Dict[str, List[Callable]] = {}
        self.post_stage_callbacks: Dict[str, List[Callable]] = {}
        
        self.logger.info("Pipeline Stage Manager initialized")
    
    def register_stage(self, stage: PipelineStage) -> bool:
        """
        Register a pipeline stage.
        
        Args:
            stage: Stage to register
            
        Returns:
            bool: True if registered successfully
        """
        with self.lock:
            if stage.config.name in self.stages:
                self.logger.warning(f"Stage {stage.config.name} already registered")
                return False
            
            self.stages[stage.config.name] = stage
            self._rebuild_execution_order()
            
            self.logger.info(f"Registered stage: {stage.config.name}")
            return True
    
    def unregister_stage(self, stage_name: str) -> bool:
        """
        Unregister a pipeline stage.
        
        Args:
            stage_name: Name of stage to remove
            
        Returns:
            bool: True if removed successfully
        """
        with self.lock:
            if stage_name not in self.stages:
                self.logger.warning(f"Stage {stage_name} not found")
                return False
            
            # Check if other stages depend on this
            dependents = self._get_dependents(stage_name)
            if dependents:
                self.logger.error(
                    f"Cannot remove {stage_name}: stages {dependents} depend on it"
                )
                return False
            
            del self.stages[stage_name]
            self._rebuild_execution_order()
            
            self.logger.info(f"Unregistered stage: {stage_name}")
            return True
    
    def enable_stage(self, stage_name: str):
        """Enable a stage."""
        with self.lock:
            if stage_name in self.stages:
                self.stages[stage_name].config.enabled = True
                self.logger.info(f"Enabled stage: {stage_name}")
    
    def disable_stage(self, stage_name: str):
        """Disable a stage."""
        with self.lock:
            if stage_name in self.stages:
                stage = self.stages[stage_name]
                if stage.config.required:
                    self.logger.warning(f"Cannot disable required stage: {stage_name}")
                    return
                
                stage.config.enabled = False
                self.logger.info(f"Disabled stage: {stage_name}")
    
    def execute_pipeline(self, initial_data: Any) -> Dict[str, StageResult]:
        """
        Execute all stages in order.
        
        Args:
            initial_data: Initial input data
            
        Returns:
            dict: Stage name -> StageResult
        """
        results = {}
        current_data = initial_data
        
        with self.lock:
            execution_order = self.stage_order.copy()
        
        for stage_name in execution_order:
            stage = self.stages.get(stage_name)
            if not stage:
                continue
            
            # Execute pre-stage callbacks
            self._execute_callbacks(self.pre_stage_callbacks.get(stage_name, []), current_data)
            
            # Execute stage
            result = stage.execute(current_data)
            results[stage_name] = result
            
            # Execute post-stage callbacks
            self._execute_callbacks(self.post_stage_callbacks.get(stage_name, []), result)
            
            # Check if stage failed
            if not result.success:
                if stage.config.required:
                    self.logger.error(f"Required stage {stage_name} failed, stopping pipeline")
                    break
                else:
                    self.logger.warning(f"Optional stage {stage_name} failed, continuing")
            
            # Update data for next stage
            if result.success and result.data is not None:
                current_data = result.data
        
        return results
    
    def execute_stage(self, stage_name: str, input_data: Any) -> Optional[StageResult]:
        """
        Execute a single stage.
        
        Args:
            stage_name: Name of stage to execute
            input_data: Input data
            
        Returns:
            StageResult or None
        """
        stage = self.stages.get(stage_name)
        if not stage:
            self.logger.error(f"Stage {stage_name} not found")
            return None
        
        return stage.execute(input_data)
    
    def register_pre_stage_callback(self, stage_name: str, callback: Callable):
        """
        Register callback to run before a stage.
        
        Args:
            stage_name: Stage name
            callback: Callback function
        """
        if stage_name not in self.pre_stage_callbacks:
            self.pre_stage_callbacks[stage_name] = []
        self.pre_stage_callbacks[stage_name].append(callback)
        self.logger.debug(f"Registered pre-stage callback for {stage_name}")
    
    def register_post_stage_callback(self, stage_name: str, callback: Callable):
        """
        Register callback to run after a stage.
        
        Args:
            stage_name: Stage name
            callback: Callback function
        """
        if stage_name not in self.post_stage_callbacks:
            self.post_stage_callbacks[stage_name] = []
        self.post_stage_callbacks[stage_name].append(callback)
        self.logger.debug(f"Registered post-stage callback for {stage_name}")
    
    def _execute_callbacks(self, callbacks: List[Callable], data: Any):
        """Execute a list of callbacks."""
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")
    
    def _rebuild_execution_order(self):
        """Rebuild stage execution order based on dependencies."""
        # Topological sort
        visited: Set[str] = set()
        order: List[str] = []
        
        def visit(stage_name: str):
            if stage_name in visited:
                return
            
            stage = self.stages.get(stage_name)
            if not stage:
                return
            
            # Visit dependencies first
            for dep in stage.config.dependencies:
                if dep in self.stages:
                    visit(dep)
            
            visited.add(stage_name)
            order.append(stage_name)
        
        # Visit all stages
        for stage_name in self.stages.keys():
            visit(stage_name)
        
        self.stage_order = order
        self.logger.debug(f"Execution order: {' → '.join(order)}")
    
    def _get_dependents(self, stage_name: str) -> List[str]:
        """Get stages that depend on the given stage."""
        dependents = []
        for name, stage in self.stages.items():
            if stage_name in stage.config.dependencies:
                dependents.append(name)
        return dependents
    
    def validate_dependencies(self) -> Dict[str, List[str]]:
        """
        Validate all stage dependencies.
        
        Returns:
            dict: Stage name -> list of missing dependencies
        """
        issues = {}
        
        for stage_name, stage in self.stages.items():
            missing = []
            for dep in stage.config.dependencies:
                if dep not in self.stages:
                    missing.append(dep)
            
            if missing:
                issues[stage_name] = missing
        
        return issues
    
    def get_stage_stats(self, stage_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a stage."""
        stage = self.stages.get(stage_name)
        if not stage:
            return None
        return stage.get_stats()
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all stages."""
        return {
            name: stage.get_stats()
            for name, stage in self.stages.items()
        }
    
    def get_execution_graph(self) -> Dict[str, Any]:
        """
        Get execution graph showing stage dependencies.
        
        Returns:
            dict: Graph representation
        """
        graph = {
            'stages': {},
            'execution_order': self.stage_order
        }
        
        for name, stage in self.stages.items():
            graph['stages'][name] = {
                'enabled': stage.config.enabled,
                'required': stage.config.required,
                'dependencies': stage.config.dependencies,
                'dependents': self._get_dependents(name),
                'state': stage.state.value
            }
        
        return graph
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all stages."""
        stats = self.get_all_stats()
        issues = self.validate_dependencies()
        
        total_executions = sum(s['executions'] for s in stats.values())
        total_successes = sum(s['successes'] for s in stats.values())
        total_failures = sum(s['failures'] for s in stats.values())
        
        return {
            'total_stages': len(self.stages),
            'enabled_stages': sum(1 for s in self.stages.values() if s.config.enabled),
            'required_stages': sum(1 for s in self.stages.values() if s.config.required),
            'execution_order': self.stage_order,
            'total_executions': total_executions,
            'total_successes': total_successes,
            'total_failures': total_failures,
            'overall_success_rate': (
                total_successes / max(total_executions, 1) * 100
            ),
            'dependency_issues': issues,
            'stages': stats
        }
