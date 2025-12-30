"""
WebSocket Optimization for Jarvis Command Center V2
Implements delta-based updates and intelligent change detection
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Set
from datetime import datetime
import psutil


@dataclass
class SystemState:
    """System state snapshot"""
    cpu: float
    memory: float
    active_tasks: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class ChangeDetector:
    """Detect significant changes in system state"""

    def __init__(
        self,
        cpu_threshold: float = 0.5,
        memory_threshold: float = 0.5,
        task_threshold: int = 0
    ):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.task_threshold = task_threshold

    def has_changed(
        self,
        old_state: Optional[SystemState],
        new_state: SystemState
    ) -> bool:
        """Check if state has changed significantly"""
        if old_state is None:
            return True

        cpu_delta = abs(new_state.cpu - old_state.cpu)
        memory_delta = abs(new_state.memory - old_state.memory)
        task_delta = abs(new_state.active_tasks - old_state.active_tasks)

        return (
            cpu_delta > self.cpu_threshold or
            memory_delta > self.memory_threshold or
            task_delta > self.task_threshold
        )

    def get_changed_fields(
        self,
        old_state: Optional[SystemState],
        new_state: SystemState
    ) -> Set[str]:
        """Get set of fields that changed"""
        if old_state is None:
            return {'cpu', 'memory', 'active_tasks', 'timestamp'}

        changed = {'timestamp'}  # Always include timestamp

        if abs(new_state.cpu - old_state.cpu) > self.cpu_threshold:
            changed.add('cpu')

        if abs(new_state.memory - old_state.memory) > self.memory_threshold:
            changed.add('memory')

        if abs(new_state.active_tasks - old_state.active_tasks) > self.task_threshold:
            changed.add('active_tasks')

        return changed


class DeltaGenerator:
    """Generate delta updates for WebSocket messages"""

    def __init__(self):
        self.change_detector = ChangeDetector()

    def generate_delta(
        self,
        old_state: Optional[SystemState],
        new_state: SystemState
    ) -> Optional[Dict[str, Any]]:
        """Generate delta message with only changed fields"""

        # Check if update needed
        if not self.change_detector.has_changed(old_state, new_state):
            return None

        # Get changed fields
        changed_fields = self.change_detector.get_changed_fields(
            old_state,
            new_state
        )

        # Build delta message
        delta = {"type": "status_delta"}

        if 'cpu' in changed_fields:
            delta['cpu'] = round(new_state.cpu, 2)

        if 'memory' in changed_fields:
            delta['memory'] = round(new_state.memory, 2)

        if 'active_tasks' in changed_fields:
            delta['active_tasks'] = new_state.active_tasks

        delta['timestamp'] = new_state.timestamp

        return delta if len(delta) > 2 else None  # Only if has data beyond type + timestamp

    def generate_full(self, state: SystemState) -> Dict[str, Any]:
        """Generate full state update"""
        return {
            "type": "status_full",
            "cpu": round(state.cpu, 2),
            "memory": round(state.memory, 2),
            "active_tasks": state.active_tasks,
            "timestamp": state.timestamp
        }


class AdaptiveUpdateScheduler:
    """Adaptive update scheduling based on change rate"""

    def __init__(
        self,
        min_interval: float = 1.0,
        max_interval: float = 5.0,
        baseline_interval: float = 2.0
    ):
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.baseline_interval = baseline_interval
        self.current_interval = baseline_interval

        self.change_history = []
        self.history_window = 10

    def record_change(self, has_change: bool):
        """Record whether state changed in this update"""
        self.change_history.append(has_change)

        # Keep only recent history
        if len(self.change_history) > self.history_window:
            self.change_history.pop(0)

        # Adjust interval based on change rate
        self._adjust_interval()

    def _adjust_interval(self):
        """Adjust update interval based on change frequency"""
        if len(self.change_history) < 3:
            return

        # Calculate change rate
        recent_changes = sum(1 for x in self.change_history[-5:] if x)
        change_rate = recent_changes / len(self.change_history[-5:])

        # Adapt interval
        if change_rate > 0.7:
            # High change rate - increase update frequency
            self.current_interval = max(
                self.min_interval,
                self.current_interval * 0.8
            )
        elif change_rate < 0.2:
            # Low change rate - decrease update frequency
            self.current_interval = min(
                self.max_interval,
                self.current_interval * 1.2
            )
        else:
            # Medium change rate - gradually return to baseline
            if self.current_interval < self.baseline_interval:
                self.current_interval = min(
                    self.baseline_interval,
                    self.current_interval * 1.1
                )
            elif self.current_interval > self.baseline_interval:
                self.current_interval = max(
                    self.baseline_interval,
                    self.current_interval * 0.9
                )

    def get_interval(self) -> float:
        """Get current update interval"""
        return self.current_interval


class WebSocketOptimizer:
    """Main WebSocket optimization coordinator"""

    def __init__(self):
        self.delta_generator = DeltaGenerator()
        self.scheduler = AdaptiveUpdateScheduler()
        self.last_state: Optional[SystemState] = None
        self.last_full_update = datetime.now()
        self.full_update_interval = 30  # Send full update every 30 seconds

        # Statistics
        self.stats = {
            'total_updates': 0,
            'delta_updates': 0,
            'full_updates': 0,
            'skipped_updates': 0,
            'bytes_sent': 0,
            'bytes_saved': 0
        }

    def get_current_state(self) -> SystemState:
        """Get current system state"""
        return SystemState(
            cpu=psutil.cpu_percent(interval=0.1),
            memory=psutil.virtual_memory().percent,
            active_tasks=3,  # Replace with actual task count
            timestamp=datetime.now().isoformat()
        )

    def should_send_full_update(self) -> bool:
        """Check if full update should be sent"""
        return (
            datetime.now() - self.last_full_update
        ).seconds >= self.full_update_interval

    def get_update(self) -> Optional[Dict[str, Any]]:
        """Get next update message (delta or full)"""
        self.stats['total_updates'] += 1
        current_state = self.get_current_state()

        # Send full update periodically
        if self.should_send_full_update():
            update = self.delta_generator.generate_full(current_state)
            self.last_full_update = datetime.now()
            self.last_state = current_state
            self.stats['full_updates'] += 1
            self.stats['bytes_sent'] += len(str(update))
            self.scheduler.record_change(True)
            return update

        # Try delta update
        delta = self.delta_generator.generate_delta(
            self.last_state,
            current_state
        )

        if delta:
            # Significant change detected
            self.last_state = current_state
            self.stats['delta_updates'] += 1
            self.stats['bytes_sent'] += len(str(delta))

            # Estimate bytes saved vs full update
            full_size = len(str(self.delta_generator.generate_full(current_state)))
            delta_size = len(str(delta))
            self.stats['bytes_saved'] += (full_size - delta_size)

            self.scheduler.record_change(True)
            return delta
        else:
            # No significant change - skip update
            self.stats['skipped_updates'] += 1
            self.scheduler.record_change(False)
            return None

    def get_update_interval(self) -> float:
        """Get adaptive update interval"""
        return self.scheduler.get_interval()

    def get_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        total = self.stats['total_updates']
        if total == 0:
            return self.stats

        return {
            **self.stats,
            'skip_rate': round(self.stats['skipped_updates'] / total * 100, 2),
            'delta_rate': round(self.stats['delta_updates'] / total * 100, 2),
            'avg_bytes_per_update': round(
                self.stats['bytes_sent'] / max(total - self.stats['skipped_updates'], 1),
                2
            ),
            'compression_ratio': round(
                self.stats['bytes_saved'] / max(self.stats['bytes_sent'], 1) * 100,
                2
            ),
            'current_interval': self.scheduler.get_interval()
        }


class ConnectionPool:
    """Manage multiple WebSocket connections efficiently"""

    def __init__(self):
        self.connections: Dict[str, Any] = {}
        self.optimizer = WebSocketOptimizer()

    def add_connection(self, conn_id: str, websocket: Any):
        """Add new WebSocket connection"""
        self.connections[conn_id] = {
            'websocket': websocket,
            'connected_at': datetime.now(),
            'messages_sent': 0
        }

    def remove_connection(self, conn_id: str):
        """Remove WebSocket connection"""
        if conn_id in self.connections:
            del self.connections[conn_id]

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connections"""
        for conn_id, conn_info in list(self.connections.items()):
            try:
                await conn_info['websocket'].send_json(message)
                conn_info['messages_sent'] += 1
            except Exception as e:
                print(f"Error sending to {conn_id}: {e}")
                self.remove_connection(conn_id)

    async def send_update(self):
        """Send optimized update to all connections"""
        update = self.optimizer.get_update()

        if update:
            await self.broadcast(update)

        return update is not None

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            'active_connections': len(self.connections),
            'total_messages': sum(
                c['messages_sent'] for c in self.connections.values()
            ),
            'optimizer_stats': self.optimizer.get_stats()
        }
