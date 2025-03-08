from datetime import datetime
import os
import sqlite3
from typing import Dict, List, Optional, Tuple, Union


class DatabaseManager:
    """Manages SQLite database operations for file metadata storage and retrieval."""
    
    def __init__(self, db_path: str = ".lfind/metadata.db"):
        """Initialize database connection and ensure tables exist."""
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database and create tables (including the seen flag)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        if self._connection is None:
            try:
                self._connection = sqlite3.connect(self.db_path)
                self._connection.row_factory = sqlite3.Row
            except sqlite3.Error as e:
                print(f"Error connecting to database: {e}")
                raise
        return self._connection

    def _init_database(self):
        """Initialize database schema."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Create files table with a 'seen' flag for scheduled updates.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    absolute_path TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL,
                    extension TEXT,
                    size INTEGER,
                    created_at TIMESTAMP,
                    modified_at TIMESTAMP,
                    last_indexed_at TIMESTAMP,
                    embedding_id INTEGER,
                    embedding_type TEXT,
                    seen INTEGER DEFAULT 0
                )
            """)

            # Create indexes for common query patterns.
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(absolute_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_type ON files(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_modified ON files(modified_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_embedding_type ON files(embedding_type)")
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def reset_seen_flags(self):
        """Reset the seen flag for all records to 0."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE files SET seen = 0")
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error resetting seen flags: {e}")
            raise

    def delete_missing_files(self) -> int:
        """
        Delete all records where the seen flag is still 0,
        indicating that these files were not encountered during the scheduled update.
        Returns the number of deleted records.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE seen = 0")
            count = cursor.rowcount
            conn.commit()
            return count
        except sqlite3.Error as e:
            print(f"Error deleting missing files: {e}")
            return 0

    def touch_file(self, file_data: Dict[str, Union[str, int, float]]) -> bool:
        """
        Evaluate and update the file record for the given file.
        This method:
          - Reads the current file stats (size, modified_at, etc.) from disk.
          - If the record does not exist, inserts a new record with seen = 1 and returns True.
          - If the record exists but is outdated (e.g., modified_at or size differ), updates the record,
            sets seen = 1, and returns True.
          - Otherwise, simply marks the record as seen (sets seen = 1) and returns False.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get file stats
            try:
                stats = os.stat(file_data['absolute_path'])
                size = stats.st_size
                created_at = datetime.fromtimestamp(stats.st_ctime)
                modified_at = datetime.fromtimestamp(stats.st_mtime)
            except (OSError, FileNotFoundError) as e:
                print(f"File stat error for {file_data['absolute_path']}: {e}")
                return False  # If file cannot be read, skip update.

            # Get file extension
            _, extension = os.path.splitext(file_data['name'])
            extension = extension.lower() if extension else None

            # Try to find an existing record.
            cursor.execute("SELECT * FROM files WHERE absolute_path = ?", (file_data['absolute_path'],))
            row = cursor.fetchone()
            requires_update = False

            if row is None:
                # No record exists: insert new record and mark as seen.
                cursor.execute("""
                    INSERT INTO files (
                        name, absolute_path, type, extension,
                        size, created_at, modified_at, last_indexed_at, seen
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
                """, (
                    file_data['name'],
                    file_data['absolute_path'],
                    file_data['type'],
                    extension,
                    size,
                    created_at,
                    modified_at
                ))
                requires_update = True
            else:
                # Record exists. Compare stored modified_at and size.
                old_modified = row['modified_at']
                old_size = row['size']

                try:
                    old_modified_dt = datetime.fromisoformat(old_modified) if old_modified else None
                except Exception:
                    old_modified_dt = None

                if (old_modified_dt is None or modified_at != old_modified_dt) or (old_size is None or size != old_size):
                    # File has changed: update record.
                    requires_update = True
                    cursor.execute("""
                        UPDATE files SET
                            name = ?,
                            type = ?,
                            extension = ?,
                            size = ?,
                            created_at = ?,
                            modified_at = ?,
                            last_indexed_at = CURRENT_TIMESTAMP,
                            seen = 1
                        WHERE absolute_path = ?
                    """, (
                        file_data['name'],
                        file_data['type'],
                        extension,
                        size,
                        created_at,
                        modified_at,
                        file_data['absolute_path']
                    ))
                else:
                    # File is up-to-date: simply mark it as seen.
                    cursor.execute("UPDATE files SET seen = 1 WHERE absolute_path = ?", (file_data['absolute_path'],))
            conn.commit()
            return requires_update
        except sqlite3.Error as e:
            print(f"Error in touch_file for {file_data['absolute_path']}: {e}")
            return False

    def get_files_by_criteria(
        self,
        directory: Optional[str] = None,
        extensions: Optional[List[str]] = None,
        file_type: Optional[str] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        modified_after: Optional[datetime] = None,
        modified_before: Optional[datetime] = None
    ) -> List[Dict[str, Union[str, int, float]]]:
        """
        Retrieve files matching the specified criteria.
        Returns a list of file metadata dictionaries.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = "SELECT * FROM files WHERE 1=1"
            params = []

            if directory:
                # Recursive filtering: files whose absolute path starts with the given directory.
                query += " AND absolute_path LIKE ?"
                params.append(directory.rstrip('/') + '/%')

            if extensions:
                query += " AND extension IN (" + ','.join('?' for _ in extensions) + ")"
                params.extend(extensions)

            if file_type:
                query += " AND type = ?"
                params.append(file_type)

            if min_size is not None:
                query += " AND size >= ?"
                params.append(min_size)

            if max_size is not None:
                query += " AND size <= ?"
                params.append(max_size)

            if modified_after:
                query += " AND modified_at >= ?"
                params.append(modified_after)

            if modified_before:
                query += " AND modified_at <= ?"
                params.append(modified_before)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error in get_files_by_criteria: {e}")
            return []

    def get_embedding_mappings(self) -> List[Tuple[int, int, str]]:
        """Get all file ID to embedding ID mappings with embedding type."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, embedding_id, embedding_type
                FROM files
                WHERE embedding_id IS NOT NULL
            """)
            return [(row['id'], row['embedding_id'], row['embedding_type']) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error in get_embedding_mappings: {e}")
            return []

    def get_file_by_id(self, file_id: int) -> Optional[Dict[str, Union[str, int, float]]]:
        """Retrieve file metadata by ID."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"Error in get_file_by_id: {e}")
            return None

    def get_files_by_embedding_ids(self, embedding_ids: List[int], embedding_type: Optional[str] = None) -> List[Dict[str, Union[str, int, float]]]:
        """
        Retrieve file metadata for files with specified embedding IDs.
        Optionally filter by embedding_type ('title' or 'content').
        Returns results in an arbitrary order.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            placeholders = ','.join('?' for _ in embedding_ids)
            query = f"SELECT * FROM files WHERE embedding_id IN ({placeholders})"
            params = list(embedding_ids)

            if embedding_type:
                query += " AND embedding_type = ?"
                params.append(embedding_type)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error in get_files_by_embedding_ids: {e}")
            return []

    def update_embedding_id(self, file_id: int, embedding_id: int, embedding_type: str = 'title') -> bool:
        """
        Update the embedding ID and type for a specific file.

        Args:
            file_id: The ID of the file record
            embedding_id: The new embedding ID to associate with this file
            embedding_type: The type of embedding ('title' or 'content')

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE files 
                SET embedding_id = ?, embedding_type = ?
                WHERE id = ?
            """, (embedding_id, embedding_type, file_id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating embedding ID: {e}")
            return False
    
    def get_files_by_embedding_type(self, embedding_type: str) -> List[Dict[str, Union[str, int, float]]]:
        """
        Retrieve all files with a specific embedding type.

        Args:
            embedding_type: The type of embedding ('title' or 'content')

        Returns:
            List of file metadata dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE embedding_type = ?", (embedding_type,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error in get_files_by_embedding_type: {e}")
            return []




### **Usage in a Scheduled Update**

# - **Step 1:** Call `reset_seen_flags()` to mark all records as unseen.
# - **Step 2:** Walk through your file system (using `os.walk` or similar). For each file/directory, prepare a `file_data` dictionary (including at least `'name'`, `'absolute_path'`, and `'type'`) and call `touch_file(file_data)`.  
#   - If `touch_file` returns `True`, you know this file is new or has been modified (and you can trigger any extra update actions, such as re-computing embeddings).
# - **Step 3:** After processing all files, call `delete_missing_files()` to remove records that were not "touched" (i.e. files that no longer exist on disk).

# This design allows you to update your metadata database in a single pass through the file system and then remove stale records in one final cleanup step.
