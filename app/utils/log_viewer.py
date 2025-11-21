"""
OptikR Log Viewer and Analysis Tool

This module provides utilities for viewing, filtering, and analyzing
structured logs in real-time with advanced search and filtering capabilities.

Author: Niklas Verhasselt
Date: November 2025
"""

import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import re

from .structured_logger import LogEntry, LogSeverity, LogCategory

# Import path utilities for EXE compatibility
from app.utils.path_utils import get_app_path


@dataclass
class LogFilter:
    """Configuration for log filtering."""
    min_level: Optional[LogSeverity] = None
    max_level: Optional[LogSeverity] = None
    categories: Optional[List[str]] = None
    operations: Optional[List[str]] = None
    search_text: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    session_id: Optional[str] = None
    thread_id: Optional[str] = None


class LogAnalyzer:
    """Analyzes log data for patterns and statistics."""
    
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []
    
    def add_logs(self, logs: List[Dict[str, Any]]) -> None:
        """Add logs for analysis."""
        self.logs.extend(logs)
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get comprehensive log statistics."""
        if not self.logs:
            return {}
        
        # Count by level
        level_counts = {}
        category_counts = {}
        operation_counts = {}
        hourly_counts = {}
        
        for log in self.logs:
            # Level statistics
            level = log.get('level', 'UNKNOWN')
            level_counts[level] = level_counts.get(level, 0) + 1
            
            # Category statistics
            category = log.get('category', 'UNKNOWN')
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Operation statistics
            operation = log.get('operation', 'UNKNOWN')
            operation_counts[operation] = operation_counts.get(operation, 0) + 1
            
            # Hourly statistics
            try:
                timestamp = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
                hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
            except (ValueError, AttributeError):
                pass
        
        return {
            'total_logs': len(self.logs),
            'level_distribution': level_counts,
            'category_distribution': category_counts,
            'operation_distribution': operation_counts,
            'hourly_distribution': hourly_counts,
            'time_range': self._get_time_range()
        }
    
    def _get_time_range(self) -> Dict[str, Optional[str]]:
        """Get time range of logs."""
        timestamps = []
        for log in self.logs:
            try:
                timestamp = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
                timestamps.append(timestamp)
            except (ValueError, AttributeError):
                pass
        
        if timestamps:
            return {
                'earliest': min(timestamps).isoformat(),
                'latest': max(timestamps).isoformat()
            }
        return {'earliest': None, 'latest': None}
    
    def find_error_patterns(self) -> List[Dict[str, Any]]:
        """Find common error patterns."""
        error_logs = [log for log in self.logs if log.get('level') in ['ERROR', 'CRITICAL']]
        
        # Group by message patterns
        patterns = {}
        for log in error_logs:
            message = log.get('message', '')
            # Simple pattern matching - group similar messages
            pattern_key = re.sub(r'\d+', 'N', message)  # Replace numbers with N
            pattern_key = re.sub(r'[a-f0-9]{8,}', 'ID', pattern_key)  # Replace IDs
            
            if pattern_key not in patterns:
                patterns[pattern_key] = {
                    'pattern': pattern_key,
                    'count': 0,
                    'examples': []
                }
            
            patterns[pattern_key]['count'] += 1
            if len(patterns[pattern_key]['examples']) < 3:
                patterns[pattern_key]['examples'].append(log)
        
        return sorted(patterns.values(), key=lambda x: x['count'], reverse=True)
    
    def get_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends from logs."""
        performance_logs = [
            log for log in self.logs 
            if log.get('category') == 'PERFORMANCE' and log.get('performance_data')
        ]
        
        if not performance_logs:
            return {}
        
        # Extract performance metrics over time
        metrics_over_time = []
        for log in performance_logs:
            perf_data = log.get('performance_data', {})
            timestamp = log.get('timestamp')
            
            if timestamp and perf_data:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    metrics_over_time.append({
                        'timestamp': dt,
                        'metrics': perf_data
                    })
                except (ValueError, AttributeError):
                    pass
        
        if not metrics_over_time:
            return {}
        
        # Sort by timestamp
        metrics_over_time.sort(key=lambda x: x['timestamp'])
        
        # Calculate trends
        return {
            'total_measurements': len(metrics_over_time),
            'time_range': {
                'start': metrics_over_time[0]['timestamp'].isoformat(),
                'end': metrics_over_time[-1]['timestamp'].isoformat()
            },
            'sample_metrics': metrics_over_time[:5]  # First 5 samples
        }


class LogViewer:
    """Real-time log viewer with filtering and search capabilities."""
    
    def __init__(self, log_file_path: str):
        self.log_file_path = Path(log_file_path)
        self.current_filter = LogFilter()
        self.analyzer = LogAnalyzer()
        
        # GUI components
        self.root = None
        self.log_display = None
        self.filter_frame = None
        self.status_label = None
        
        # Real-time monitoring
        self.monitoring = False
        self.monitor_thread = None
        self.last_file_size = 0
        
        # Callbacks
        self.log_handlers: List[Callable[[Dict[str, Any]], None]] = []
    
    def create_gui(self) -> tk.Tk:
        """Create the log viewer GUI."""
        self.root = tk.Tk()
        self.root.title("OptikR Log Viewer")
        self.root.geometry("1200x800")
        
        # Create main layout
        self._create_menu_bar()
        self._create_filter_panel()
        self._create_log_display()
        self._create_status_bar()
        
        return self.root
    
    def _create_menu_bar(self) -> None:
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Log File", command=self._open_log_file)
        file_menu.add_command(label="Export Filtered Logs", command=self._export_logs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Clear Display", command=self._clear_display)
        view_menu.add_command(label="Refresh", command=self._refresh_logs)
        view_menu.add_separator()
        view_menu.add_command(label="Show Statistics", command=self._show_statistics)
        view_menu.add_command(label="Show Error Patterns", command=self._show_error_patterns)
        
        # Monitor menu
        monitor_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Monitor", menu=monitor_menu)
        monitor_menu.add_command(label="Start Real-time Monitoring", command=self._start_monitoring)
        monitor_menu.add_command(label="Stop Monitoring", command=self._stop_monitoring)
    
    def _create_filter_panel(self) -> None:
        """Create filter panel."""
        self.filter_frame = ttk.LabelFrame(self.root, text="Filters", padding="5")
        self.filter_frame.pack(fill="x", padx=5, pady=5)
        
        # Filter controls in grid layout
        row = 0
        
        # Log level filter
        ttk.Label(self.filter_frame, text="Min Level:").grid(row=row, column=0, sticky="w", padx=5)
        self.level_var = tk.StringVar(value="DEBUG")
        level_combo = ttk.Combobox(self.filter_frame, textvariable=self.level_var,
                                  values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                  state="readonly", width=10)
        level_combo.grid(row=row, column=1, padx=5)
        level_combo.bind("<<ComboboxSelected>>", self._on_filter_change)
        
        # Category filter
        ttk.Label(self.filter_frame, text="Category:").grid(row=row, column=2, sticky="w", padx=5)
        self.category_var = tk.StringVar()
        category_combo = ttk.Combobox(self.filter_frame, textvariable=self.category_var,
                                     values=["", "SYSTEM", "CAPTURE", "OCR", "TRANSLATION", 
                                            "OVERLAY", "PERFORMANCE", "ERROR", "USER_ACTION"],
                                     width=12)
        category_combo.grid(row=row, column=3, padx=5)
        category_combo.bind("<<ComboboxSelected>>", self._on_filter_change)
        
        row += 1
        
        # Search text
        ttk.Label(self.filter_frame, text="Search:").grid(row=row, column=0, sticky="w", padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(self.filter_frame, textvariable=self.search_var, width=30)
        search_entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5)
        search_entry.bind("<KeyRelease>", self._on_filter_change)
        
        # Filter buttons
        ttk.Button(self.filter_frame, text="Apply Filter", 
                  command=self._apply_filter).grid(row=row, column=3, padx=5)
        ttk.Button(self.filter_frame, text="Clear Filter", 
                  command=self._clear_filter).grid(row=row, column=4, padx=5)
    
    def _create_log_display(self) -> None:
        """Create log display area."""
        # Create notebook for different views
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Raw log view
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Log Entries")
        
        self.log_display = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, 
                                                    font=("Consolas", 9))
        self.log_display.pack(fill="both", expand=True)
        
        # Structured view
        structured_frame = ttk.Frame(notebook)
        notebook.add(structured_frame, text="Structured View")
        
        # Create treeview for structured display
        columns = ("Timestamp", "Level", "Category", "Operation", "Message")
        self.tree_view = ttk.Treeview(structured_frame, columns=columns, show="headings")
        
        for col in columns:
            self.tree_view.heading(col, text=col)
            self.tree_view.column(col, width=150)
        
        # Add scrollbars to treeview
        tree_scroll_y = ttk.Scrollbar(structured_frame, orient="vertical", command=self.tree_view.yview)
        tree_scroll_x = ttk.Scrollbar(structured_frame, orient="horizontal", command=self.tree_view.xview)
        self.tree_view.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.tree_view.pack(side="left", fill="both", expand=True)
        tree_scroll_y.pack(side="right", fill="y")
        tree_scroll_x.pack(side="bottom", fill="x")
        
        # Bind double-click to show details
        self.tree_view.bind("<Double-1>", self._show_log_details)
    
    def _create_status_bar(self) -> None:
        """Create status bar."""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", side="bottom")
        
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side="left", padx=5)
        
        # Monitoring indicator
        self.monitor_label = ttk.Label(status_frame, text="●", foreground="red")
        self.monitor_label.pack(side="right", padx=5)
    
    def _open_log_file(self) -> None:
        """Open log file dialog."""
        file_path = filedialog.askopenfilename(
            title="Select Log File",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")]
        )
        
        if file_path:
            self.log_file_path = Path(file_path)
            self._refresh_logs()
    
    def _refresh_logs(self) -> None:
        """Refresh log display."""
        if not self.log_file_path.exists():
            self.status_label.config(text="Log file not found")
            return
        
        try:
            logs = self._load_logs()
            filtered_logs = self._apply_current_filter(logs)
            self._display_logs(filtered_logs)
            
            self.status_label.config(text=f"Loaded {len(filtered_logs)} of {len(logs)} log entries")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load logs: {e}")
    
    def _load_logs(self) -> List[Dict[str, Any]]:
        """Load logs from file."""
        logs = []
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Try to parse as JSON (structured format)
                        log_data = json.loads(line)
                        logs.append(log_data)
                    except json.JSONDecodeError:
                        # Try to parse as simple format
                        parts = line.split(' - ', 3)
                        if len(parts) >= 4:
                            timestamp, level, category, message = parts
                            logs.append({
                                'timestamp': timestamp,
                                'level': level,
                                'category': category,
                                'operation': 'unknown',
                                'message': message,
                                'line_number': line_num
                            })
                        
        except Exception as e:
            raise Exception(f"Error reading log file: {e}")
        
        return logs
    
    def _apply_current_filter(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply current filter to logs."""
        filtered_logs = []
        
        for log in logs:
            if self._matches_filter(log):
                filtered_logs.append(log)
        
        return filtered_logs
    
    def _matches_filter(self, log: Dict[str, Any]) -> bool:
        """Check if log entry matches current filter."""
        # Level filter
        if self.current_filter.min_level:
            try:
                log_level = LogSeverity[log.get('level', 'INFO')]
                if log_level.value < self.current_filter.min_level.value:
                    return False
            except KeyError:
                pass
        
        # Category filter
        if self.current_filter.categories:
            if log.get('category') not in self.current_filter.categories:
                return False
        
        # Search text filter
        if self.current_filter.search_text:
            search_text = self.current_filter.search_text.lower()
            searchable_text = f"{log.get('message', '')} {log.get('operation', '')}".lower()
            if search_text not in searchable_text:
                return False
        
        return True
    
    def _display_logs(self, logs: List[Dict[str, Any]]) -> None:
        """Display logs in both views."""
        # Clear displays
        self.log_display.delete(1.0, tk.END)
        for item in self.tree_view.get_children():
            self.tree_view.delete(item)
        
        # Display in raw view
        for log in logs:
            timestamp = log.get('timestamp', 'Unknown')
            level = log.get('level', 'INFO')
            category = log.get('category', 'GENERAL')
            operation = log.get('operation', 'unknown')
            message = log.get('message', '')
            
            # Color coding for levels
            if level == 'ERROR':
                color_tag = 'error'
            elif level == 'WARNING':
                color_tag = 'warning'
            elif level == 'CRITICAL':
                color_tag = 'critical'
            else:
                color_tag = 'normal'
            
            log_line = f"[{timestamp}] {level:8} | {category:12} | {operation:15} | {message}\n"
            self.log_display.insert(tk.END, log_line, color_tag)
        
        # Configure text colors
        self.log_display.tag_config('error', foreground='red')
        self.log_display.tag_config('warning', foreground='orange')
        self.log_display.tag_config('critical', foreground='darkred', background='yellow')
        self.log_display.tag_config('normal', foreground='black')
        
        # Display in structured view
        for log in logs:
            timestamp = log.get('timestamp', 'Unknown')
            level = log.get('level', 'INFO')
            category = log.get('category', 'GENERAL')
            operation = log.get('operation', 'unknown')
            message = log.get('message', '')[:100]  # Truncate for display
            
            item = self.tree_view.insert('', 'end', values=(timestamp, level, category, operation, message))
            
            # Store full log data
            self.tree_view.set(item, 'full_data', json.dumps(log))
        
        # Auto-scroll to bottom
        self.log_display.see(tk.END)
        
        # Update analyzer
        self.analyzer.logs = logs
    
    def _on_filter_change(self, event=None) -> None:
        """Handle filter change."""
        # Update current filter
        level_text = self.level_var.get()
        if level_text:
            try:
                self.current_filter.min_level = LogSeverity[level_text]
            except KeyError:
                self.current_filter.min_level = None
        
        category_text = self.category_var.get()
        if category_text:
            self.current_filter.categories = [category_text]
        else:
            self.current_filter.categories = None
        
        search_text = self.search_var.get().strip()
        if search_text:
            self.current_filter.search_text = search_text
        else:
            self.current_filter.search_text = None
    
    def _apply_filter(self) -> None:
        """Apply current filter."""
        self._on_filter_change()
        self._refresh_logs()
    
    def _clear_filter(self) -> None:
        """Clear all filters."""
        self.level_var.set("DEBUG")
        self.category_var.set("")
        self.search_var.set("")
        self.current_filter = LogFilter()
        self._refresh_logs()
    
    def _clear_display(self) -> None:
        """Clear log display."""
        self.log_display.delete(1.0, tk.END)
        for item in self.tree_view.get_children():
            self.tree_view.delete(item)
    
    def _show_log_details(self, event) -> None:
        """Show detailed log information."""
        selection = self.tree_view.selection()
        if not selection:
            return
        
        item = selection[0]
        full_data = self.tree_view.set(item, 'full_data')
        
        if full_data:
            try:
                log_data = json.loads(full_data)
                self._show_log_detail_window(log_data)
            except json.JSONDecodeError:
                pass
    
    def _show_log_detail_window(self, log_data: Dict[str, Any]) -> None:
        """Show log detail in separate window."""
        detail_window = tk.Toplevel(self.root)
        detail_window.title("Log Entry Details")
        detail_window.geometry("600x400")
        
        # Create text widget with scrollbar
        text_widget = scrolledtext.ScrolledText(detail_window, wrap=tk.WORD)
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Format log data
        formatted_data = json.dumps(log_data, indent=2, default=str, ensure_ascii=False)
        text_widget.insert(tk.END, formatted_data)
        text_widget.config(state=tk.DISABLED)
    
    def _show_statistics(self) -> None:
        """Show log statistics."""
        stats = self.analyzer.get_log_statistics()
        
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Log Statistics")
        stats_window.geometry("500x400")
        
        text_widget = scrolledtext.ScrolledText(stats_window, wrap=tk.WORD)
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        
        formatted_stats = json.dumps(stats, indent=2, default=str, ensure_ascii=False)
        text_widget.insert(tk.END, formatted_stats)
        text_widget.config(state=tk.DISABLED)
    
    def _show_error_patterns(self) -> None:
        """Show error patterns analysis."""
        patterns = self.analyzer.find_error_patterns()
        
        patterns_window = tk.Toplevel(self.root)
        patterns_window.title("Error Patterns")
        patterns_window.geometry("700x500")
        
        text_widget = scrolledtext.ScrolledText(patterns_window, wrap=tk.WORD)
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        
        if patterns:
            text_widget.insert(tk.END, "Common Error Patterns:\n\n")
            for i, pattern in enumerate(patterns[:10], 1):  # Top 10 patterns
                text_widget.insert(tk.END, f"{i}. Pattern: {pattern['pattern']}\n")
                text_widget.insert(tk.END, f"   Count: {pattern['count']}\n")
                text_widget.insert(tk.END, f"   Examples:\n")
                for example in pattern['examples'][:2]:  # Show 2 examples
                    text_widget.insert(tk.END, f"     - {example.get('message', '')}\n")
                text_widget.insert(tk.END, "\n")
        else:
            text_widget.insert(tk.END, "No error patterns found.")
        
        text_widget.config(state=tk.DISABLED)
    
    def _export_logs(self) -> None:
        """Export filtered logs to file."""
        file_path = filedialog.asksaveasfilename(
            title="Export Logs",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                logs = self._load_logs()
                filtered_logs = self._apply_current_filter(logs)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    if file_path.endswith('.json'):
                        json.dump(filtered_logs, f, indent=2, default=str, ensure_ascii=False)
                    else:
                        for log in filtered_logs:
                            f.write(f"{log}\n")
                
                messagebox.showinfo("Success", f"Exported {len(filtered_logs)} log entries to {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export logs: {e}")
    
    def _start_monitoring(self) -> None:
        """Start real-time log monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_label.config(foreground="green")
        self.status_label.config(text="Real-time monitoring active")
        
        self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self.monitor_thread.start()
    
    def _stop_monitoring(self) -> None:
        """Stop real-time log monitoring."""
        self.monitoring = False
        self.monitor_label.config(foreground="red")
        self.status_label.config(text="Monitoring stopped")
    
    def _monitor_worker(self) -> None:
        """Background worker for real-time monitoring."""
        while self.monitoring:
            try:
                if self.log_file_path.exists():
                    current_size = self.log_file_path.stat().st_size
                    if current_size > self.last_file_size:
                        # File has grown, refresh logs
                        self.root.after(0, self._refresh_logs)
                        self.last_file_size = current_size
                
                time.sleep(1.0)  # Check every second
                
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5.0)  # Wait longer on error


def create_log_viewer(log_file_path: str) -> LogViewer:
    """
    Create and configure a log viewer for the specified log file.
    
    Args:
        log_file_path: Path to the log file to monitor.
        
    Returns:
        Configured LogViewer instance.
    """
    return LogViewer(log_file_path)


def main():
    """Main function for standalone log viewer."""
    import sys
    
    # Find the most recent log file (EXE-compatible)
    log_dir = get_app_path("logs")
    if log_dir.exists():
        log_files = sorted(log_dir.glob("error-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        log_file = str(log_files[0]) if log_files else str(log_dir / "error-*.log")
    else:
        log_file = str(log_dir / "error-*.log")
    
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    
    viewer = create_log_viewer(log_file)
    root = viewer.create_gui()
    
    # Load initial logs
    viewer._refresh_logs()
    
    # Start the GUI
    root.mainloop()


if __name__ == "__main__":
    main()