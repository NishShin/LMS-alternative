from pathlib import Path
from utils.common import load_json_file, save_json_file
import datetime


class DataManager:
    
    def __init__(self, data_dir, drive_service=None):
        self.data_dir = Path(data_dir) if isinstance(data_dir, str) else data_dir
        self.drive_service = drive_service
        self.lms_root_id = self._load_lms_root_id()
        
        self.assignments_file = self.data_dir / "assignments.json"
        self.students_file = self.data_dir / "students.json"
        self.submissions_file = self.data_dir / "submissions.json"
    
    def _load_lms_root_id(self):
        config = load_json_file("lms_config.json", {})
        return config.get("lms_root_id")
    
    def _load_from_drive_or_local(self, filepath, default=None):
        if self.drive_service and self.lms_root_id:
            filename = filepath.name
            try:
                file = self.drive_service.find_file(filename, self.lms_root_id)
                if file:
                    content = self.drive_service.read_file_content(file['id'])
                    if content:
                        import json
                        return json.loads(content)
            except Exception as e:
                print(f"Error loading from Drive: {e}")
        
        return load_json_file(filepath, default)
    
    def _save_to_local_and_drive(self, filepath, data):
        save_json_file(filepath, data)
        
        if self.drive_service and self.lms_root_id:
            filename = filepath.name
            try:
                existing = self.drive_service.find_file(filename, self.lms_root_id)
                if existing:
                    self.drive_service.update_file(existing['id'], str(filepath))
                else:
                    self.drive_service.upload_file(str(filepath), parent_id=self.lms_root_id)
            except Exception as e:
                print(f"Error saving to Drive: {e}")
    
    def load_assignments(self):
        assignments = self._load_from_drive_or_local(self.assignments_file, [])
        
        modified = False
        for i, assignment in enumerate(assignments):
            if 'id' not in assignment:
                assignment['id'] = str(datetime.datetime.now().timestamp()) + str(i)
                modified = True
        
        if modified:
            self.save_assignments(assignments)
        
        return assignments
    
    def load_students(self):
        return self._load_from_drive_or_local(self.students_file, [])
    
    def load_submissions(self):
        return self._load_from_drive_or_local(self.submissions_file, [])
    
    def save_assignments(self, assignments):
        self._save_to_local_and_drive(self.assignments_file, assignments)
    
    def save_students(self, students):
        self._save_to_local_and_drive(self.students_file, students)
    
    def save_submissions(self, submissions):
        self._save_to_local_and_drive(self.submissions_file, submissions)