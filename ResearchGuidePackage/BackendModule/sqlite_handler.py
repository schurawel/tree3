import sqlite3
import logging

logger = logging.getLogger(__name__)

class SQLiteHandler:
    def __init__(self):
        self.db_path = None
        self.conn = None
        self.cursor = None

    def set_db_path(self, db_path):
        self.db_path = db_path

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")

    def create_table(self, table_name, columns):
        try:
            self.connect()
            columns_str = ", ".join(columns)
            query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
            self.cursor.execute(query)
            self.conn.commit()
            logger.info(f"Table created: {table_name}")
        except sqlite3.Error as e:
            logger.error(f"Error creating table: {e}")
            raise
        finally:
            self.close()

    def insert_data(self, table_name, data):
        try:
            self.connect()
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data.values()])
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            self.cursor.execute(query, tuple(data.values()))
            self.conn.commit()
            logger.debug(f"Data inserted into {table_name}: {data}")
        except sqlite3.Error as e:
            logger.error(f"Error inserting data: {e}")
            raise
        finally:
            self.close()

    def update_data(self, table_name, data, condition):
        try:
            self.connect()
            set_values = ", ".join([f"{key} = ?" for key in data.keys()])
            query = f"UPDATE {table_name} SET {set_values} WHERE {condition}"
            self.cursor.execute(query, tuple(data.values()))
            self.conn.commit()
            logger.debug(f"Data updated in {table_name}: {data} with condition: {condition}")
        except sqlite3.Error as e:
            logger.error(f"Error updating data: {e}")
            raise
        finally:
            self.close()

    def read_data(self, table_name, columns, condition=None):
        try:
            self.connect()
            columns_str = ", ".join(columns)
            query = f"SELECT {columns_str} FROM {table_name}"
            if condition:
                query += f" WHERE {condition}"
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            logger.debug(f"Data read from {table_name} with condition: {condition}")
            return rows
        except sqlite3.Error as e:
            logger.error(f"Error reading data: {e}")
            raise
        finally:
            self.close()

    def delete_data(self, table_name, condition):
        try:
            self.connect()
            query = f"DELETE FROM {table_name} WHERE {condition}"
            self.cursor.execute(query)
            self.conn.commit()
            logger.debug(f"Data deleted from {table_name} with condition: {condition}")
        except sqlite3.Error as e:
            logger.error(f"Error deleting data: {e}")
            raise
        finally:
            self.close()

    def file_exists(self, file_path):
        try:
            self.connect()
            query = "SELECT 1 FROM nodes WHERE file_path = ?"
            self.cursor.execute(query, (file_path,))
            result = self.cursor.fetchone()
            return result is not None
        except sqlite3.Error as e:
            logger.error(f"Error checking file existence: {e}")
            raise
        finally:
            self.close()

    def download_file(self, file_path, destination):
        try:
            self.connect()
            query = "SELECT content FROM nodes WHERE file_path = ?"
            self.cursor.execute(query, (file_path,))
            result = self.cursor.fetchone()
            if result:
                with open(destination, 'wb') as file:
                    file.write(result[0])
                logger.info(f"File downloaded to: {destination}")
            else:
                logger.warning(f"File not found in database: {file_path}")
        except sqlite3.Error as e:
            logger.error(f"Error downloading file: {e}")
            raise
        finally:
            self.close()

    def table_exists(self, table_name):
        try:
            self.connect()
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
            self.cursor.execute(query, (table_name,))
            result = self.cursor.fetchone()
            return result is not None
        except sqlite3.Error as e:
            logger.error(f"Error checking table existence: {e}")
            raise
        finally:
            self.close()
