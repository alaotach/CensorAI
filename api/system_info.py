from datetime import datetime

class SystemInfo:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._current_time = None
            self._current_user = None
            self._initialized = True

    def update(self, time_str=None, user=None):
        if time_str:
            try:
                self._current_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                raise ValueError("Time must be in format: YYYY-MM-DD HH:MM:SS")
        if user:
            self._current_user = user

    @property
    def current_time(self):
        return self._current_time or datetime.utcnow()

    @property
    def current_user(self):
        return self._current_user or 'system'

    def get_formatted_time(self):
        return self.current_time.strftime('%Y-%m-%d %H:%M:%S')