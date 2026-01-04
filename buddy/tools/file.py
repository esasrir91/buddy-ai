import json
import os
import shutil
import stat
import hashlib
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Dict, Union

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, log_error, log_info


class FileTools(Toolkit):
    def __init__(
        self,
        base_dir: Optional[Path] = None,
        save_files: bool = True,
        read_files: bool = True,
        list_files: bool = True,
        search_files: bool = True,
        create_directories: bool = True,
        delete_files: bool = True,
        move_files: bool = True,
        copy_files: bool = True,
        file_info: bool = True,
        append_files: bool = True,
        backup_files: bool = True,
        text_operations: bool = True,
        advanced_search: bool = True,
        **kwargs,
    ):
        self.base_dir: Path = base_dir or Path.cwd()

        tools: List[Any] = []
        if save_files:
            tools.append(self.save_file)
        if read_files:
            tools.append(self.read_file)
        if list_files:
            tools.append(self.list_files)
        if search_files:
            tools.append(self.search_files)
        if create_directories:
            tools.extend([self.create_directory, self.create_file])
        if delete_files:
            tools.extend([self.delete_file, self.delete_directory])
        if move_files:
            tools.extend([self.move_file, self.rename_file])
        if copy_files:
            tools.append(self.copy_file)
        if file_info:
            tools.extend([self.get_file_info, self.file_exists, self.get_file_size, self.get_file_hash])
        if append_files:
            tools.append(self.append_to_file)
        if backup_files:
            tools.extend([self.backup_file, self.restore_backup])
        if text_operations:
            tools.extend([self.find_in_file, self.replace_in_file, self.count_lines])
        if advanced_search:
            tools.extend([
                self.search_text_in_files, 
                self.search_by_extension, 
                self.search_by_size,
                self.search_by_date,
                self.search_with_regex,
                self.find_duplicates,
                self.search_empty_files,
                self.grep_search
            ])

        super().__init__(name="file_tools", tools=tools, **kwargs)

    def save_file(self, contents: str, file_name: str, overwrite: bool = True) -> str:
        """Saves the contents to a file called `file_name` and returns the file name if successful.

        :param contents: The contents to save.
        :param file_name: The name of the file to save to.
        :param overwrite: Overwrite the file if it already exists.
        :return: The file name if successful, otherwise returns an error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            log_debug(f"Saving contents to {file_path}")
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            if file_path.exists() and not overwrite:
                return f"File {file_name} already exists"
            file_path.write_text(contents)
            log_info(f"Saved: {file_path}")
            return str(file_name)
        except Exception as e:
            log_error(f"Error saving to file: {e}")
            return f"Error saving to file: {e}"

    def read_file(self, file_name: str) -> str:
        """Reads the contents of the file `file_name` and returns the contents if successful.

        :param file_name: The name of the file to read.
        :return: The contents of the file if successful, otherwise returns an error message.
        """
        try:
            log_info(f"Reading file: {file_name}")
            file_path = self.base_dir.joinpath(file_name)
            contents = file_path.read_text(encoding="utf-8")
            return str(contents)
        except Exception as e:
            log_error(f"Error reading file: {e}")
            return f"Error reading file: {e}"

    def list_files(self) -> str:
        """Returns a list of files in the base directory

        :return: The contents of the file if successful, otherwise returns an error message.
        """
        try:
            log_info(f"Reading files in : {self.base_dir}")
            return json.dumps([str(file_path) for file_path in self.base_dir.iterdir()], indent=4)
        except Exception as e:
            log_error(f"Error reading files: {e}")
            return f"Error reading files: {e}"

    def search_files(self, pattern: str) -> str:
        """Searches for files in the base directory that match the pattern

        :param pattern: The pattern to search for, e.g. "*.txt", "file*.csv", "**/*.py".
        :return: JSON formatted list of matching file paths, or error message.
        """
        try:
            if not pattern or not pattern.strip():
                return "Error: Pattern cannot be empty"

            log_debug(f"Searching files in {self.base_dir} with pattern {pattern}")
            matching_files = list(self.base_dir.glob(pattern))

            file_paths = [str(file_path) for file_path in matching_files]

            result = {
                "pattern": pattern,
                "base_directory": str(self.base_dir),
                "matches_found": len(file_paths),
                "files": file_paths,
            }
            log_debug(f"Found {len(file_paths)} files matching pattern {pattern}")
            return json.dumps(result, indent=2)

        except Exception as e:
            error_msg = f"Error searching files with pattern '{pattern}': {e}"
            log_error(error_msg)
            return error_msg

    def create_file(self, file_name: str, contents: str = "") -> str:
        """Creates a new file with optional initial contents.

        :param file_name: The name of the file to create.
        :param contents: Initial contents for the file (optional).
        :return: Success message or error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            if file_path.exists():
                return f"File {file_name} already exists"
            
            # Create parent directories if they don't exist
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_path.write_text(contents, encoding="utf-8")
            log_info(f"Created file: {file_path}")
            return f"Created file: {file_name}"
        except Exception as e:
            log_error(f"Error creating file: {e}")
            return f"Error creating file: {e}"

    def create_directory(self, dir_name: str) -> str:
        """Creates a new directory.

        :param dir_name: The name/path of the directory to create.
        :return: Success message or error message.
        """
        try:
            dir_path = self.base_dir.joinpath(dir_name)
            if dir_path.exists():
                return f"Directory {dir_name} already exists"
            
            dir_path.mkdir(parents=True, exist_ok=True)
            log_info(f"Created directory: {dir_path}")
            return f"Created directory: {dir_name}"
        except Exception as e:
            log_error(f"Error creating directory: {e}")
            return f"Error creating directory: {e}"

    def delete_file(self, file_name: str, confirm: bool = False) -> str:
        """Deletes a file.

        :param file_name: The name of the file to delete.
        :param confirm: Confirmation flag to prevent accidental deletion.
        :return: Success message or error message.
        """
        try:
            if not confirm:
                return "Confirmation required. Set confirm=True to delete the file."
            
            file_path = self.base_dir.joinpath(file_name)
            if not file_path.exists():
                return f"File {file_name} does not exist"
            
            if file_path.is_dir():
                return f"{file_name} is a directory, use delete_directory instead"
            
            file_path.unlink()
            log_info(f"Deleted file: {file_path}")
            return f"Deleted file: {file_name}"
        except Exception as e:
            log_error(f"Error deleting file: {e}")
            return f"Error deleting file: {e}"

    def delete_directory(self, dir_name: str, confirm: bool = False) -> str:
        """Deletes a directory and all its contents.

        :param dir_name: The name of the directory to delete.
        :param confirm: Confirmation flag to prevent accidental deletion.
        :return: Success message or error message.
        """
        try:
            if not confirm:
                return "Confirmation required. Set confirm=True to delete the directory."
            
            dir_path = self.base_dir.joinpath(dir_name)
            if not dir_path.exists():
                return f"Directory {dir_name} does not exist"
            
            if not dir_path.is_dir():
                return f"{dir_name} is not a directory"
            
            shutil.rmtree(dir_path)
            log_info(f"Deleted directory: {dir_path}")
            return f"Deleted directory: {dir_name}"
        except Exception as e:
            log_error(f"Error deleting directory: {e}")
            return f"Error deleting directory: {e}"

    def move_file(self, source: str, destination: str) -> str:
        """Moves a file from source to destination.

        :param source: The source file path.
        :param destination: The destination file path.
        :return: Success message or error message.
        """
        try:
            source_path = self.base_dir.joinpath(source)
            dest_path = self.base_dir.joinpath(destination)
            
            if not source_path.exists():
                return f"Source file {source} does not exist"
            
            # Create destination directory if it doesn't exist
            if not dest_path.parent.exists():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source_path), str(dest_path))
            log_info(f"Moved file from {source_path} to {dest_path}")
            return f"Moved file from {source} to {destination}"
        except Exception as e:
            log_error(f"Error moving file: {e}")
            return f"Error moving file: {e}"

    def rename_file(self, old_name: str, new_name: str) -> str:
        """Renames a file.

        :param old_name: The current name of the file.
        :param new_name: The new name for the file.
        :return: Success message or error message.
        """
        try:
            old_path = self.base_dir.joinpath(old_name)
            new_path = self.base_dir.joinpath(new_name)
            
            if not old_path.exists():
                return f"File {old_name} does not exist"
            
            if new_path.exists():
                return f"File {new_name} already exists"
            
            old_path.rename(new_path)
            log_info(f"Renamed file from {old_path} to {new_path}")
            return f"Renamed file from {old_name} to {new_name}"
        except Exception as e:
            log_error(f"Error renaming file: {e}")
            return f"Error renaming file: {e}"

    def copy_file(self, source: str, destination: str, overwrite: bool = False) -> str:
        """Copies a file from source to destination.

        :param source: The source file path.
        :param destination: The destination file path.
        :param overwrite: Whether to overwrite if destination exists.
        :return: Success message or error message.
        """
        try:
            source_path = self.base_dir.joinpath(source)
            dest_path = self.base_dir.joinpath(destination)
            
            if not source_path.exists():
                return f"Source file {source} does not exist"
            
            if dest_path.exists() and not overwrite:
                return f"Destination file {destination} already exists"
            
            # Create destination directory if it doesn't exist
            if not dest_path.parent.exists():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(str(source_path), str(dest_path))
            log_info(f"Copied file from {source_path} to {dest_path}")
            return f"Copied file from {source} to {destination}"
        except Exception as e:
            log_error(f"Error copying file: {e}")
            return f"Error copying file: {e}"

    def get_file_info(self, file_name: str) -> str:
        """Gets detailed information about a file or directory.

        :param file_name: The name of the file/directory.
        :return: JSON formatted file information or error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            if not file_path.exists():
                return f"File/directory {file_name} does not exist"
            
            stat_info = file_path.stat()
            
            info = {
                "name": file_name,
                "absolute_path": str(file_path.absolute()),
                "type": "directory" if file_path.is_dir() else "file",
                "size_bytes": stat_info.st_size,
                "size_readable": self._format_size(stat_info.st_size),
                "created": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                "permissions": oct(stat_info.st_mode)[-3:],
                "is_readable": os.access(file_path, os.R_OK),
                "is_writable": os.access(file_path, os.W_OK),
                "is_executable": os.access(file_path, os.X_OK),
            }
            
            if file_path.is_file():
                info["mime_type"] = mimetypes.guess_type(str(file_path))[0]
                info["suffix"] = file_path.suffix
            
            return json.dumps(info, indent=2)
        except Exception as e:
            log_error(f"Error getting file info: {e}")
            return f"Error getting file info: {e}"

    def file_exists(self, file_name: str) -> str:
        """Checks if a file or directory exists.

        :param file_name: The name of the file/directory to check.
        :return: JSON with existence status.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            result = {
                "file_name": file_name,
                "exists": file_path.exists(),
                "is_file": file_path.is_file() if file_path.exists() else None,
                "is_directory": file_path.is_dir() if file_path.exists() else None,
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            log_error(f"Error checking file existence: {e}")
            return f"Error checking file existence: {e}"

    def get_file_size(self, file_name: str) -> str:
        """Gets the size of a file.

        :param file_name: The name of the file.
        :return: File size information or error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            if not file_path.exists():
                return f"File {file_name} does not exist"
            
            if file_path.is_dir():
                # Calculate directory size
                total_size = sum(f.stat().st_size for f in file_path.rglob('*') if f.is_file())
            else:
                total_size = file_path.stat().st_size
            
            result = {
                "file_name": file_name,
                "size_bytes": total_size,
                "size_readable": self._format_size(total_size),
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            log_error(f"Error getting file size: {e}")
            return f"Error getting file size: {e}"

    def get_file_hash(self, file_name: str, algorithm: str = "md5") -> str:
        """Calculates the hash of a file.

        :param file_name: The name of the file.
        :param algorithm: Hash algorithm (md5, sha1, sha256, sha512).
        :return: File hash or error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            if not file_path.exists():
                return f"File {file_name} does not exist"
            
            if file_path.is_dir():
                return f"{file_name} is a directory"
            
            # Validate algorithm
            if algorithm.lower() not in ['md5', 'sha1', 'sha256', 'sha512']:
                return f"Unsupported hash algorithm: {algorithm}"
            
            hash_obj = hashlib.new(algorithm.lower())
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            result = {
                "file_name": file_name,
                "algorithm": algorithm.lower(),
                "hash": hash_obj.hexdigest(),
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            log_error(f"Error calculating file hash: {e}")
            return f"Error calculating file hash: {e}"

    def append_to_file(self, file_name: str, contents: str) -> str:
        """Appends content to an existing file.

        :param file_name: The name of the file to append to.
        :param contents: The content to append.
        :return: Success message or error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            
            # Create file if it doesn't exist
            if not file_path.exists():
                file_path.touch()
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(contents)
            
            log_info(f"Appended to file: {file_path}")
            return f"Appended content to {file_name}"
        except Exception as e:
            log_error(f"Error appending to file: {e}")
            return f"Error appending to file: {e}"

    def backup_file(self, file_name: str, backup_suffix: str = ".backup") -> str:
        """Creates a backup copy of a file.

        :param file_name: The name of the file to backup.
        :param backup_suffix: Suffix to add to the backup file.
        :return: Success message or error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            if not file_path.exists():
                return f"File {file_name} does not exist"
            
            # Add timestamp to backup suffix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_name}{backup_suffix}_{timestamp}"
            backup_path = self.base_dir.joinpath(backup_name)
            
            shutil.copy2(str(file_path), str(backup_path))
            log_info(f"Created backup: {backup_path}")
            return f"Created backup: {backup_name}"
        except Exception as e:
            log_error(f"Error creating backup: {e}")
            return f"Error creating backup: {e}"

    def restore_backup(self, backup_file_name: str, original_file_name: str) -> str:
        """Restores a file from a backup.

        :param backup_file_name: The name of the backup file.
        :param original_file_name: The name of the original file to restore.
        :return: Success message or error message.
        """
        try:
            backup_path = self.base_dir.joinpath(backup_file_name)
            original_path = self.base_dir.joinpath(original_file_name)
            
            if not backup_path.exists():
                return f"Backup file {backup_file_name} does not exist"
            
            shutil.copy2(str(backup_path), str(original_path))
            log_info(f"Restored file from backup: {original_path}")
            return f"Restored {original_file_name} from {backup_file_name}"
        except Exception as e:
            log_error(f"Error restoring from backup: {e}")
            return f"Error restoring from backup: {e}"

    def find_in_file(self, file_name: str, search_text: str, case_sensitive: bool = True) -> str:
        """Searches for text within a file and returns matching lines.

        :param file_name: The name of the file to search.
        :param search_text: The text to search for.
        :param case_sensitive: Whether the search should be case sensitive.
        :return: JSON with search results or error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            if not file_path.exists():
                return f"File {file_name} does not exist"
            
            if file_path.is_dir():
                return f"{file_name} is a directory"
            
            matches = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line_to_search = line if case_sensitive else line.lower()
                    text_to_find = search_text if case_sensitive else search_text.lower()
                    
                    if text_to_find in line_to_search:
                        matches.append({
                            "line_number": line_num,
                            "line_content": line.rstrip('\n\r'),
                            "column": line_to_search.find(text_to_find) + 1
                        })
            
            result = {
                "file_name": file_name,
                "search_text": search_text,
                "case_sensitive": case_sensitive,
                "matches_found": len(matches),
                "matches": matches
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            log_error(f"Error searching in file: {e}")
            return f"Error searching in file: {e}"

    def replace_in_file(self, file_name: str, search_text: str, replace_text: str, case_sensitive: bool = True) -> str:
        """Replaces text within a file.

        :param file_name: The name of the file to modify.
        :param search_text: The text to search for.
        :param replace_text: The text to replace with.
        :param case_sensitive: Whether the search should be case sensitive.
        :return: Success message with replacement count or error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            if not file_path.exists():
                return f"File {file_name} does not exist"
            
            if file_path.is_dir():
                return f"{file_name} is a directory"
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Perform replacement
            if case_sensitive:
                new_content = content.replace(search_text, replace_text)
                count = content.count(search_text)
            else:
                # Case insensitive replacement
                import re
                pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                new_content = pattern.sub(replace_text, content)
                count = len(pattern.findall(content))
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            log_info(f"Replaced {count} occurrences in {file_path}")
            return f"Replaced {count} occurrences of '{search_text}' with '{replace_text}' in {file_name}"
        except Exception as e:
            log_error(f"Error replacing in file: {e}")
            return f"Error replacing in file: {e}"

    def count_lines(self, file_name: str) -> str:
        """Counts the number of lines in a file.

        :param file_name: The name of the file.
        :return: Line count information or error message.
        """
        try:
            file_path = self.base_dir.joinpath(file_name)
            if not file_path.exists():
                return f"File {file_name} does not exist"
            
            if file_path.is_dir():
                return f"{file_name} is a directory"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            non_empty_lines = sum(1 for line in lines if line.strip())
            empty_lines = total_lines - non_empty_lines
            
            result = {
                "file_name": file_name,
                "total_lines": total_lines,
                "non_empty_lines": non_empty_lines,
                "empty_lines": empty_lines,
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            log_error(f"Error counting lines: {e}")
            return f"Error counting lines: {e}"

    def _format_size(self, size_bytes: int) -> str:
        """Formats file size in human-readable format.

        :param size_bytes: Size in bytes.
        :return: Formatted size string.
        """
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    def search_text_in_files(self, search_text: str, file_pattern: str = "**/*", case_sensitive: bool = True, max_results: int = 100) -> str:
        """Searches for text across multiple files in the directory tree.

        :param search_text: The text to search for.
        :param file_pattern: Glob pattern for files to search (default: all files).
        :param case_sensitive: Whether the search should be case sensitive.
        :param max_results: Maximum number of matches to return.
        :return: JSON with search results across files.
        """
        try:
            if not search_text or not search_text.strip():
                return "Error: Search text cannot be empty"

            log_debug(f"Searching for '{search_text}' in files matching '{file_pattern}'")
            
            matching_files = list(self.base_dir.glob(file_pattern))
            results = []
            total_matches = 0
            
            for file_path in matching_files:
                if not file_path.is_file():
                    continue
                    
                try:
                    # Skip binary files by checking for null bytes in first 1024 bytes
                    with open(file_path, 'rb') as f:
                        sample = f.read(1024)
                        if b'\0' in sample:
                            continue
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_matches = []
                        for line_num, line in enumerate(f, 1):
                            line_to_search = line if case_sensitive else line.lower()
                            text_to_find = search_text if case_sensitive else search_text.lower()
                            
                            if text_to_find in line_to_search:
                                file_matches.append({
                                    "line_number": line_num,
                                    "line_content": line.rstrip('\n\r'),
                                    "column": line_to_search.find(text_to_find) + 1
                                })
                                total_matches += 1
                                
                                if total_matches >= max_results:
                                    break
                        
                        if file_matches:
                            results.append({
                                "file_path": str(file_path.relative_to(self.base_dir)),
                                "absolute_path": str(file_path),
                                "matches_in_file": len(file_matches),
                                "matches": file_matches
                            })
                            
                        if total_matches >= max_results:
                            break
                            
                except (UnicodeDecodeError, PermissionError):
                    continue
            
            result = {
                "search_text": search_text,
                "file_pattern": file_pattern,
                "case_sensitive": case_sensitive,
                "total_files_searched": len([f for f in matching_files if f.is_file()]),
                "files_with_matches": len(results),
                "total_matches": total_matches,
                "max_results_reached": total_matches >= max_results,
                "results": results
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            log_error(f"Error searching text in files: {e}")
            return f"Error searching text in files: {e}"

    def search_by_extension(self, extensions: Union[str, List[str]], include_info: bool = False) -> str:
        """Searches for files by their extensions.

        :param extensions: File extension(s) to search for (e.g., '.py', ['.py', '.txt']).
        :param include_info: Whether to include detailed file information.
        :return: JSON with files matching the extensions.
        """
        try:
            if isinstance(extensions, str):
                extensions = [extensions]
            
            # Ensure extensions start with dot
            extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
            
            log_debug(f"Searching for files with extensions: {extensions}")
            
            results = []
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in [ext.lower() for ext in extensions]:
                    file_info = {
                        "file_path": str(file_path.relative_to(self.base_dir)),
                        "absolute_path": str(file_path),
                        "extension": file_path.suffix,
                        "name": file_path.name
                    }
                    
                    if include_info:
                        stat_info = file_path.stat()
                        file_info.update({
                            "size_bytes": stat_info.st_size,
                            "size_readable": self._format_size(stat_info.st_size),
                            "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        })
                    
                    results.append(file_info)
            
            result = {
                "extensions": extensions,
                "files_found": len(results),
                "files": results
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            log_error(f"Error searching by extension: {e}")
            return f"Error searching by extension: {e}"

    def search_by_size(self, min_size: int = 0, max_size: Optional[int] = None, size_unit: str = "bytes") -> str:
        """Searches for files by size range.

        :param min_size: Minimum file size.
        :param max_size: Maximum file size (optional).
        :param size_unit: Size unit ('bytes', 'kb', 'mb', 'gb').
        :return: JSON with files matching the size criteria.
        """
        try:
            # Convert sizes to bytes
            multipliers = {
                'bytes': 1,
                'kb': 1024,
                'mb': 1024 * 1024,
                'gb': 1024 * 1024 * 1024
            }
            
            if size_unit.lower() not in multipliers:
                return f"Invalid size unit: {size_unit}. Use: bytes, kb, mb, gb"
            
            multiplier = multipliers[size_unit.lower()]
            min_bytes = min_size * multiplier
            max_bytes = max_size * multiplier if max_size is not None else None
            
            log_debug(f"Searching for files with size range: {min_bytes} - {max_bytes} bytes")
            
            results = []
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    
                    if size >= min_bytes and (max_bytes is None or size <= max_bytes):
                        results.append({
                            "file_path": str(file_path.relative_to(self.base_dir)),
                            "absolute_path": str(file_path),
                            "size_bytes": size,
                            "size_readable": self._format_size(size),
                            "name": file_path.name
                        })
            
            # Sort by size (largest first)
            results.sort(key=lambda x: x["size_bytes"], reverse=True)
            
            result = {
                "min_size": f"{min_size} {size_unit}",
                "max_size": f"{max_size} {size_unit}" if max_size else "unlimited",
                "files_found": len(results),
                "files": results
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            log_error(f"Error searching by size: {e}")
            return f"Error searching by size: {e}"

    def search_by_date(self, date_type: str = "modified", days_ago: int = 7, comparison: str = "newer") -> str:
        """Searches for files by date criteria.

        :param date_type: Type of date ('modified', 'created', 'accessed').
        :param days_ago: Number of days ago as reference point.
        :param comparison: 'newer' or 'older' than the reference date.
        :return: JSON with files matching the date criteria.
        """
        try:
            if date_type not in ['modified', 'created', 'accessed']:
                return "Invalid date_type. Use: modified, created, accessed"
            
            if comparison not in ['newer', 'older']:
                return "Invalid comparison. Use: newer, older"
            
            from datetime import datetime, timedelta
            reference_date = datetime.now() - timedelta(days=days_ago)
            reference_timestamp = reference_date.timestamp()
            
            log_debug(f"Searching for files {comparison} than {days_ago} days ago ({reference_date})")
            
            results = []
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file():
                    stat_info = file_path.stat()
                    
                    if date_type == 'modified':
                        file_timestamp = stat_info.st_mtime
                    elif date_type == 'created':
                        file_timestamp = stat_info.st_ctime
                    else:  # accessed
                        file_timestamp = stat_info.st_atime
                    
                    if (comparison == 'newer' and file_timestamp > reference_timestamp) or \
                       (comparison == 'older' and file_timestamp < reference_timestamp):
                        results.append({
                            "file_path": str(file_path.relative_to(self.base_dir)),
                            "absolute_path": str(file_path),
                            "name": file_path.name,
                            f"{date_type}_date": datetime.fromtimestamp(file_timestamp).isoformat(),
                            "size_readable": self._format_size(stat_info.st_size)
                        })
            
            # Sort by date (newest first)
            results.sort(key=lambda x: x[f"{date_type}_date"], reverse=True)
            
            result = {
                "date_type": date_type,
                "days_ago": days_ago,
                "comparison": comparison,
                "reference_date": reference_date.isoformat(),
                "files_found": len(results),
                "files": results
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            log_error(f"Error searching by date: {e}")
            return f"Error searching by date: {e}"

    def search_with_regex(self, pattern: str, file_pattern: str = "**/*", max_results: int = 100) -> str:
        """Searches for files containing text that matches a regex pattern.

        :param pattern: Regular expression pattern to search for.
        :param file_pattern: Glob pattern for files to search.
        :param max_results: Maximum number of matches to return.
        :return: JSON with regex search results.
        """
        try:
            compiled_pattern = re.compile(pattern)
            log_debug(f"Searching with regex pattern: {pattern}")
            
            matching_files = list(self.base_dir.glob(file_pattern))
            results = []
            total_matches = 0
            
            for file_path in matching_files:
                if not file_path.is_file():
                    continue
                    
                try:
                    # Skip binary files
                    with open(file_path, 'rb') as f:
                        sample = f.read(1024)
                        if b'\0' in sample:
                            continue
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_matches = []
                        for line_num, line in enumerate(f, 1):
                            matches = list(compiled_pattern.finditer(line))
                            for match in matches:
                                file_matches.append({
                                    "line_number": line_num,
                                    "line_content": line.rstrip('\n\r'),
                                    "match": match.group(),
                                    "start_column": match.start() + 1,
                                    "end_column": match.end() + 1,
                                    "groups": match.groups() if match.groups() else []
                                })
                                total_matches += 1
                                
                                if total_matches >= max_results:
                                    break
                            
                            if total_matches >= max_results:
                                break
                        
                        if file_matches:
                            results.append({
                                "file_path": str(file_path.relative_to(self.base_dir)),
                                "absolute_path": str(file_path),
                                "matches_in_file": len(file_matches),
                                "matches": file_matches
                            })
                            
                        if total_matches >= max_results:
                            break
                            
                except (UnicodeDecodeError, PermissionError, re.error):
                    continue
            
            result = {
                "regex_pattern": pattern,
                "file_pattern": file_pattern,
                "total_files_searched": len([f for f in matching_files if f.is_file()]),
                "files_with_matches": len(results),
                "total_matches": total_matches,
                "max_results_reached": total_matches >= max_results,
                "results": results
            }
            
            return json.dumps(result, indent=2)
            
        except re.error as e:
            return f"Invalid regex pattern: {e}"
        except Exception as e:
            log_error(f"Error searching with regex: {e}")
            return f"Error searching with regex: {e}"

    def find_duplicates(self, algorithm: str = "md5", min_size: int = 0) -> str:
        """Finds duplicate files based on content hash.

        :param algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256').
        :param min_size: Minimum file size to consider (in bytes).
        :return: JSON with duplicate file groups.
        """
        try:
            if algorithm.lower() not in ['md5', 'sha1', 'sha256', 'sha512']:
                return f"Unsupported hash algorithm: {algorithm}"
            
            log_debug(f"Finding duplicates using {algorithm} hash")
            
            file_hashes = {}
            processed_files = 0
            
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file() and file_path.stat().st_size >= min_size:
                    try:
                        hash_obj = hashlib.new(algorithm.lower())
                        with open(file_path, 'rb') as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                hash_obj.update(chunk)
                        
                        file_hash = hash_obj.hexdigest()
                        file_info = {
                            "path": str(file_path.relative_to(self.base_dir)),
                            "absolute_path": str(file_path),
                            "size": file_path.stat().st_size,
                            "size_readable": self._format_size(file_path.stat().st_size)
                        }
                        
                        if file_hash not in file_hashes:
                            file_hashes[file_hash] = []
                        file_hashes[file_hash].append(file_info)
                        processed_files += 1
                        
                    except (PermissionError, OSError):
                        continue
            
            # Find duplicates (groups with more than one file)
            duplicate_groups = {hash_val: files for hash_val, files in file_hashes.items() if len(files) > 1}
            
            # Calculate total duplicate size
            total_duplicate_size = 0
            for files in duplicate_groups.values():
                # Size of duplicates (excluding the original)
                total_duplicate_size += files[0]["size"] * (len(files) - 1)
            
            result = {
                "algorithm": algorithm,
                "min_size_bytes": min_size,
                "total_files_processed": processed_files,
                "duplicate_groups_found": len(duplicate_groups),
                "total_duplicate_files": sum(len(files) - 1 for files in duplicate_groups.values()),
                "total_duplicate_size": total_duplicate_size,
                "total_duplicate_size_readable": self._format_size(total_duplicate_size),
                "duplicate_groups": [
                    {
                        "hash": hash_val,
                        "count": len(files),
                        "size": files[0]["size"],
                        "size_readable": files[0]["size_readable"],
                        "files": files
                    }
                    for hash_val, files in duplicate_groups.items()
                ]
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            log_error(f"Error finding duplicates: {e}")
            return f"Error finding duplicates: {e}"

    def search_empty_files(self, include_directories: bool = False) -> str:
        """Finds empty files and optionally empty directories.

        :param include_directories: Whether to include empty directories.
        :return: JSON with empty files and directories.
        """
        try:
            log_debug("Searching for empty files and directories")
            
            empty_files = []
            empty_dirs = []
            
            for item_path in self.base_dir.rglob('*'):
                if item_path.is_file() and item_path.stat().st_size == 0:
                    empty_files.append({
                        "path": str(item_path.relative_to(self.base_dir)),
                        "absolute_path": str(item_path),
                        "name": item_path.name
                    })
                elif include_directories and item_path.is_dir():
                    # Check if directory is empty
                    try:
                        if not any(item_path.iterdir()):
                            empty_dirs.append({
                                "path": str(item_path.relative_to(self.base_dir)),
                                "absolute_path": str(item_path),
                                "name": item_path.name
                            })
                    except PermissionError:
                        continue
            
            result = {
                "empty_files_found": len(empty_files),
                "empty_directories_found": len(empty_dirs) if include_directories else "not_searched",
                "empty_files": empty_files,
                "empty_directories": empty_dirs if include_directories else []
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            log_error(f"Error searching for empty files: {e}")
            return f"Error searching for empty files: {e}"

    def grep_search(self, pattern: str, file_pattern: str = "**/*", context_lines: int = 0, case_sensitive: bool = True, whole_word: bool = False, max_results: int = 100) -> str:
        """Advanced grep-like search with context lines and options.

        :param pattern: Text pattern to search for.
        :param file_pattern: Glob pattern for files to search.
        :param context_lines: Number of context lines to show around matches.
        :param case_sensitive: Whether search should be case sensitive.
        :param whole_word: Whether to match whole words only.
        :param max_results: Maximum number of matches to return.
        :return: JSON with detailed search results including context.
        """
        try:
            if not pattern or not pattern.strip():
                return "Error: Search pattern cannot be empty"
            
            log_debug(f"Grep search for pattern: {pattern}")
            
            # Prepare search pattern
            if whole_word:
                search_pattern = re.compile(r'\b' + re.escape(pattern) + r'\b', 
                                          re.IGNORECASE if not case_sensitive else 0)
            else:
                if case_sensitive:
                    search_func = lambda line: pattern in line
                else:
                    pattern_lower = pattern.lower()
                    search_func = lambda line: pattern_lower in line.lower()
            
            matching_files = list(self.base_dir.glob(file_pattern))
            results = []
            total_matches = 0
            
            for file_path in matching_files:
                if not file_path.is_file():
                    continue
                    
                try:
                    # Skip binary files
                    with open(file_path, 'rb') as f:
                        sample = f.read(1024)
                        if b'\0' in sample:
                            continue
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    file_matches = []
                    for line_num, line in enumerate(lines):
                        line_content = line.rstrip('\n\r')
                        
                        # Check for match
                        if whole_word:
                            match = search_pattern.search(line_content)
                            if match:
                                match_found = True
                                match_start = match.start()
                                match_end = match.end()
                            else:
                                match_found = False
                        else:
                            match_found = search_func(line_content)
                            if match_found:
                                if case_sensitive:
                                    match_start = line_content.find(pattern)
                                else:
                                    match_start = line_content.lower().find(pattern.lower())
                                match_end = match_start + len(pattern)
                        
                        if match_found:
                            # Get context lines
                            context_before = []
                            context_after = []
                            
                            if context_lines > 0:
                                start_idx = max(0, line_num - context_lines)
                                end_idx = min(len(lines), line_num + context_lines + 1)
                                
                                for i in range(start_idx, line_num):
                                    context_before.append({
                                        "line_number": i + 1,
                                        "content": lines[i].rstrip('\n\r')
                                    })
                                
                                for i in range(line_num + 1, end_idx):
                                    context_after.append({
                                        "line_number": i + 1,
                                        "content": lines[i].rstrip('\n\r')
                                    })
                            
                            file_matches.append({
                                "line_number": line_num + 1,
                                "line_content": line_content,
                                "match_start_column": match_start + 1,
                                "match_end_column": match_end + 1,
                                "context_before": context_before,
                                "context_after": context_after
                            })
                            
                            total_matches += 1
                            if total_matches >= max_results:
                                break
                    
                    if file_matches:
                        results.append({
                            "file_path": str(file_path.relative_to(self.base_dir)),
                            "absolute_path": str(file_path),
                            "matches_in_file": len(file_matches),
                            "matches": file_matches
                        })
                    
                    if total_matches >= max_results:
                        break
                        
                except (UnicodeDecodeError, PermissionError):
                    continue
            
            result = {
                "pattern": pattern,
                "file_pattern": file_pattern,
                "case_sensitive": case_sensitive,
                "whole_word": whole_word,
                "context_lines": context_lines,
                "total_files_searched": len([f for f in matching_files if f.is_file()]),
                "files_with_matches": len(results),
                "total_matches": total_matches,
                "max_results_reached": total_matches >= max_results,
                "results": results
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            log_error(f"Error in grep search: {e}")
            return f"Error in grep search: {e}"

