import json
from typing import Any, Dict, List, Optional, Union

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    from sqlalchemy import Engine, create_engine, MetaData, Table, Column, Integer, String, DateTime, Boolean, Float, Text
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.sql.expression import text
    from sqlalchemy.sql import select, insert, update, delete, func
    from sqlalchemy.schema import CreateTable, DropTable, CreateIndex, DropIndex
    from sqlalchemy.types import TypeEngine
except ImportError:
    raise ImportError("`sqlalchemy` not installed")


class SQLTools(Toolkit):
    def __init__(
        self,
        db_url: Optional[str] = None,
        db_engine: Optional[Engine] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        schema: Optional[str] = None,
        dialect: Optional[str] = None,
        tables: Optional[Dict[str, Any]] = None,
        list_tables: bool = True,
        describe_table: bool = True,
        run_sql_query: bool = True,
        create_table: bool = True,
        drop_table: bool = True,
        insert_data: bool = True,
        update_data: bool = True,
        delete_data: bool = True,
        create_index: bool = True,
        drop_index: bool = True,
        backup_table: bool = True,
        get_table_info: bool = True,
        analyze_table: bool = True,
        get_db_size: bool = True,
        list_views: bool = True,
        list_indexes: bool = True,
        get_foreign_keys: bool = True,
        get_primary_keys: bool = True,
        execute_transaction: bool = True,
        get_table_size: bool = True,
        vacuum_analyze: bool = True,
        get_query_plan: bool = True,
        duplicate_table_structure: bool = True,
        **kwargs,
    ):
        # Get the database engine
        _engine: Optional[Engine] = db_engine
        if _engine is None and db_url is not None:
            _engine = create_engine(db_url)
        elif user and password and host and port and dialect:
            if schema is not None:
                _engine = create_engine(f"{dialect}://{user}:{password}@{host}:{port}/{schema}")
            else:
                _engine = create_engine(f"{dialect}://{user}:{password}@{host}:{port}")

        if _engine is None:
            raise ValueError("Could not build the database connection")

        # Database connection
        self.db_engine: Engine = _engine
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.db_engine)
        self.metadata = MetaData()

        self.schema = schema

        # Tables this toolkit can access
        self.tables: Optional[Dict[str, Any]] = tables

        tools: List[Any] = []
        if list_tables:
            tools.append(self.list_tables)
        if describe_table:
            tools.append(self.describe_table)
        if run_sql_query:
            tools.append(self.run_sql_query)
        if create_table:
            tools.append(self.create_table)
        if drop_table:
            tools.append(self.drop_table)
        if insert_data:
            tools.append(self.insert_data)
        if update_data:
            tools.append(self.update_data)
        if delete_data:
            tools.append(self.delete_data)
        if create_index:
            tools.append(self.create_index)
        if drop_index:
            tools.append(self.drop_index)
        if backup_table:
            tools.append(self.backup_table)
        if get_table_info:
            tools.append(self.get_table_info)
        if analyze_table:
            tools.append(self.analyze_table)
        if get_db_size:
            tools.append(self.get_db_size)
        if list_views:
            tools.append(self.list_views)
        if list_indexes:
            tools.append(self.list_indexes)
        if get_foreign_keys:
            tools.append(self.get_foreign_keys)
        if get_primary_keys:
            tools.append(self.get_primary_keys)
        if execute_transaction:
            tools.append(self.execute_transaction)
        if get_table_size:
            tools.append(self.get_table_size)
        if vacuum_analyze:
            tools.append(self.vacuum_analyze)
        if get_query_plan:
            tools.append(self.get_query_plan)
        if duplicate_table_structure:
            tools.append(self.duplicate_table_structure)

        super().__init__(name="sql_tools", tools=tools, **kwargs)

    def list_tables(self) -> str:
        """Use this function to get a list of table names in the database.

        Returns:
            str: list of tables in the database.
        """
        if self.tables is not None:
            return json.dumps(self.tables)

        try:
            log_debug("listing tables in the database")
            inspector = inspect(self.db_engine)
            if self.schema:
                table_names = inspector.get_table_names(schema=self.schema)
            else:
                table_names = inspector.get_table_names()
            log_debug(f"table_names: {table_names}")
            return json.dumps(table_names)
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return f"Error getting tables: {e}"

    def describe_table(self, table_name: str) -> str:
        """Use this function to describe a table with comprehensive schema information.

        Args:
            table_name (str): The name of the table to get the schema for.

        Returns:
            str: Comprehensive schema information including columns, constraints, and indexes.
        """

        try:
            log_debug(f"Describing table: {table_name}")
            inspector = inspect(self.db_engine)
            
            # Get column information
            table_schema = inspector.get_columns(table_name, schema=self.schema)
            columns = [
                {
                    "name": column["name"], 
                    "type": str(column["type"]), 
                    "nullable": column["nullable"],
                    "default": column.get("default"),
                    "autoincrement": column.get("autoincrement", False)
                }
                for column in table_schema
            ]
            
            # Get constraints
            try:
                primary_keys = inspector.get_pk_constraint(table_name, schema=self.schema)
                foreign_keys = inspector.get_foreign_keys(table_name, schema=self.schema)
                unique_constraints = inspector.get_unique_constraints(table_name, schema=self.schema)
                check_constraints = inspector.get_check_constraints(table_name, schema=self.schema)
            except:
                primary_keys = foreign_keys = unique_constraints = check_constraints = []
            
            # Get indexes
            try:
                indexes = inspector.get_indexes(table_name, schema=self.schema)
            except:
                indexes = []
            
            table_description = {
                "table_name": table_name,
                "columns": columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "unique_constraints": unique_constraints,
                "check_constraints": check_constraints,
                "indexes": indexes
            }
            
            return json.dumps(table_description, default=str)
            
        except Exception as e:
            logger.error(f"Error getting table schema: {e}")
            return f"Error getting table schema: {e}"

    def run_sql_query(self, query: str, limit: Optional[int] = 10) -> str:
        """Use this function to run a SQL query and return the result.

        Args:
            query (str): The query to run.
            limit (int, optional): The number of rows to return. Defaults to 10. Use `None` to show all results.
        Returns:
            str: Result of the SQL query.
        Notes:
            - The result may be empty if the query does not return any data.
        """

        try:
            return json.dumps(self.run_sql(sql=query, limit=limit), default=str)
        except Exception as e:
            logger.error(f"Error running query: {e}")
            return f"Error running query: {e}"

    def run_sql(self, sql: str, limit: Optional[int] = None) -> List[dict]:
        """Internal function to run a sql query.

        Args:
            sql (str): The sql query to run.
            limit (int, optional): The number of rows to return. Defaults to None.

        Returns:
            List[dict]: The result of the query.
        """
        log_debug(f"Running sql |\n{sql}")

        with self.Session() as sess, sess.begin():
            result = sess.execute(text(sql))

            # Check if the operation has returned rows.
            try:
                if limit:
                    rows = result.fetchmany(limit)
                else:
                    rows = result.fetchall()
                return [row._asdict() for row in rows]
            except Exception as e:
                logger.error(f"Error while executing SQL: {e}")
                return []

    def create_table(self, table_name: str, columns: List[Dict[str, Any]]) -> str:
        """Create a new table with specified columns.

        Args:
            table_name (str): Name of the table to create.
            columns (List[Dict[str, Any]]): List of column definitions. Each dict should have 'name', 'type', and optionally 'nullable', 'primary_key', 'default'.
                Example: [{"name": "id", "type": "Integer", "primary_key": True}, {"name": "name", "type": "String(100)", "nullable": False}]

        Returns:
            str: Success or error message.
        """
        try:
            log_debug(f"Creating table: {table_name}")
            
            # Map string types to SQLAlchemy types
            type_mapping = {
                "Integer": Integer,
                "String": String,
                "Text": Text,
                "Boolean": Boolean,
                "Float": Float,
                "DateTime": DateTime,
            }
            
            table_columns = []
            for col in columns:
                col_type = col.get("type", "String")
                
                # Handle parameterized types like String(100)
                if "(" in col_type:
                    type_name = col_type.split("(")[0]
                    param = col_type.split("(")[1].split(")")[0]
                    if type_name in type_mapping:
                        if type_name == "String":
                            sql_type = type_mapping[type_name](int(param))
                        else:
                            sql_type = type_mapping[type_name]
                    else:
                        sql_type = String(100)  # Default fallback
                else:
                    sql_type = type_mapping.get(col_type, String)
                
                column = Column(
                    col["name"],
                    sql_type,
                    nullable=col.get("nullable", True),
                    primary_key=col.get("primary_key", False),
                    default=col.get("default")
                )
                table_columns.append(column)
            
            table = Table(table_name, self.metadata, *table_columns)
            create_stmt = CreateTable(table)
            
            with self.Session() as sess, sess.begin():
                sess.execute(create_stmt)
                
            return f"Table '{table_name}' created successfully."
            
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return f"Error creating table: {e}"

    def drop_table(self, table_name: str) -> str:
        """Drop a table from the database.

        Args:
            table_name (str): Name of the table to drop.

        Returns:
            str: Success or error message.
        """
        try:
            log_debug(f"Dropping table: {table_name}")
            
            # Reflect the table
            table = Table(table_name, self.metadata, autoload_with=self.db_engine, schema=self.schema)
            drop_stmt = DropTable(table)
            
            with self.Session() as sess, sess.begin():
                sess.execute(drop_stmt)
                
            return f"Table '{table_name}' dropped successfully."
            
        except Exception as e:
            logger.error(f"Error dropping table: {e}")
            return f"Error dropping table: {e}"

    def insert_data(self, table_name: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> str:
        """Insert data into a table.

        Args:
            table_name (str): Name of the table to insert data into.
            data (Union[Dict[str, Any], List[Dict[str, Any]]]): Data to insert. Can be a single row (dict) or multiple rows (list of dicts).

        Returns:
            str: Success message with number of rows inserted or error message.
        """
        try:
            log_debug(f"Inserting data into table: {table_name}")
            
            # Ensure data is a list
            if isinstance(data, dict):
                data = [data]
            
            # Reflect the table
            table = Table(table_name, self.metadata, autoload_with=self.db_engine, schema=self.schema)
            
            with self.Session() as sess, sess.begin():
                result = sess.execute(insert(table), data)
                rows_affected = result.rowcount
                
            return f"Successfully inserted {rows_affected} row(s) into '{table_name}'."
            
        except Exception as e:
            logger.error(f"Error inserting data: {e}")
            return f"Error inserting data: {e}"

    def update_data(self, table_name: str, set_values: Dict[str, Any], where_clause: str) -> str:
        """Update data in a table.

        Args:
            table_name (str): Name of the table to update.
            set_values (Dict[str, Any]): Dictionary of column-value pairs to update.
            where_clause (str): WHERE clause condition (without 'WHERE' keyword).

        Returns:
            str: Success message with number of rows affected or error message.
        """
        try:
            log_debug(f"Updating data in table: {table_name}")
            
            # Reflect the table
            table = Table(table_name, self.metadata, autoload_with=self.db_engine, schema=self.schema)
            
            stmt = update(table).values(**set_values).where(text(where_clause))
            
            with self.Session() as sess, sess.begin():
                result = sess.execute(stmt)
                rows_affected = result.rowcount
                
            return f"Successfully updated {rows_affected} row(s) in '{table_name}'."
            
        except Exception as e:
            logger.error(f"Error updating data: {e}")
            return f"Error updating data: {e}"

    def delete_data(self, table_name: str, where_clause: str) -> str:
        """Delete data from a table.

        Args:
            table_name (str): Name of the table to delete from.
            where_clause (str): WHERE clause condition (without 'WHERE' keyword).

        Returns:
            str: Success message with number of rows deleted or error message.
        """
        try:
            log_debug(f"Deleting data from table: {table_name}")
            
            # Reflect the table
            table = Table(table_name, self.metadata, autoload_with=self.db_engine, schema=self.schema)
            
            stmt = delete(table).where(text(where_clause))
            
            with self.Session() as sess, sess.begin():
                result = sess.execute(stmt)
                rows_affected = result.rowcount
                
            return f"Successfully deleted {rows_affected} row(s) from '{table_name}'."
            
        except Exception as e:
            logger.error(f"Error deleting data: {e}")
            return f"Error deleting data: {e}"

    def create_index(self, index_name: str, table_name: str, column_names: List[str], unique: bool = False) -> str:
        """Create an index on a table.

        Args:
            index_name (str): Name of the index to create.
            table_name (str): Name of the table.
            column_names (List[str]): List of column names to include in the index.
            unique (bool): Whether the index should be unique. Defaults to False.

        Returns:
            str: Success or error message.
        """
        try:
            log_debug(f"Creating index: {index_name} on table: {table_name}")
            
            # Reflect the table
            table = Table(table_name, self.metadata, autoload_with=self.db_engine, schema=self.schema)
            
            columns = [table.c[col_name] for col_name in column_names]
            
            from sqlalchemy import Index
            index = Index(index_name, *columns, unique=unique)
            create_stmt = CreateIndex(index)
            
            with self.Session() as sess, sess.begin():
                sess.execute(create_stmt)
                
            return f"Index '{index_name}' created successfully on table '{table_name}'."
            
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return f"Error creating index: {e}"

    def drop_index(self, index_name: str, table_name: Optional[str] = None) -> str:
        """Drop an index from the database.

        Args:
            index_name (str): Name of the index to drop.
            table_name (Optional[str]): Name of the table (required for some databases).

        Returns:
            str: Success or error message.
        """
        try:
            log_debug(f"Dropping index: {index_name}")
            
            if table_name:
                # Reflect the table
                table = Table(table_name, self.metadata, autoload_with=self.db_engine, schema=self.schema)
                
                from sqlalchemy import Index
                index = Index(index_name, table.c.keys()[0])  # Dummy index for drop
                drop_stmt = DropIndex(index)
            else:
                # Direct SQL for databases that support dropping by name
                drop_stmt = text(f"DROP INDEX {index_name}")
            
            with self.Session() as sess, sess.begin():
                sess.execute(drop_stmt)
                
            return f"Index '{index_name}' dropped successfully."
            
        except Exception as e:
            logger.error(f"Error dropping index: {e}")
            return f"Error dropping index: {e}"

    def backup_table(self, table_name: str, backup_table_name: Optional[str] = None) -> str:
        """Create a backup copy of a table.

        Args:
            table_name (str): Name of the table to backup.
            backup_table_name (Optional[str]): Name for the backup table. If None, will use table_name_backup.

        Returns:
            str: Success or error message.
        """
        try:
            if backup_table_name is None:
                backup_table_name = f"{table_name}_backup"
                
            log_debug(f"Creating backup of table: {table_name} as {backup_table_name}")
            
            sql = f"CREATE TABLE {backup_table_name} AS SELECT * FROM {table_name}"
            
            with self.Session() as sess, sess.begin():
                sess.execute(text(sql))
                
            return f"Backup table '{backup_table_name}' created successfully from '{table_name}'."
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return f"Error creating backup: {e}"

    def get_table_info(self, table_name: str) -> str:
        """Get comprehensive information about a table including size, row count, and structure.

        Args:
            table_name (str): Name of the table.

        Returns:
            str: JSON string with table information.
        """
        try:
            log_debug(f"Getting table info for: {table_name}")
            
            inspector = inspect(self.db_engine)
            
            # Get table schema
            columns = inspector.get_columns(table_name, schema=self.schema)
            
            # Get row count
            with self.Session() as sess:
                count_result = sess.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = count_result.scalar()
            
            # Get indexes
            indexes = inspector.get_indexes(table_name, schema=self.schema)
            
            # Get foreign keys
            foreign_keys = inspector.get_foreign_keys(table_name, schema=self.schema)
            
            # Get primary keys
            primary_keys = inspector.get_pk_constraint(table_name, schema=self.schema)
            
            table_info = {
                "table_name": table_name,
                "row_count": row_count,
                "columns": columns,
                "indexes": indexes,
                "foreign_keys": foreign_keys,
                "primary_keys": primary_keys
            }
            
            return json.dumps(table_info, default=str)
            
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            return f"Error getting table info: {e}"

    def analyze_table(self, table_name: str) -> str:
        """Analyze table data and provide statistics.

        Args:
            table_name (str): Name of the table to analyze.

        Returns:
            str: JSON string with table analysis.
        """
        try:
            log_debug(f"Analyzing table: {table_name}")
            
            inspector = inspect(self.db_engine)
            columns = inspector.get_columns(table_name, schema=self.schema)
            
            analysis = {"table_name": table_name, "column_stats": {}}
            
            with self.Session() as sess:
                for column in columns:
                    col_name = column["name"]
                    col_type = str(column["type"])
                    
                    # Basic stats for all columns
                    count_query = f"SELECT COUNT({col_name}) as count, COUNT(DISTINCT {col_name}) as distinct_count FROM {table_name}"
                    result = sess.execute(text(count_query))
                    stats = result.fetchone()._asdict()
                    
                    analysis["column_stats"][col_name] = {
                        "type": col_type,
                        "count": stats["count"],
                        "distinct_count": stats["distinct_count"],
                        "null_count": stats["count"] - stats["count"]  # This would need adjustment based on actual null handling
                    }
                    
                    # Additional stats for numeric columns
                    if any(num_type in col_type.lower() for num_type in ["int", "float", "decimal", "numeric"]):
                        try:
                            numeric_query = f"SELECT MIN({col_name}) as min_val, MAX({col_name}) as max_val, AVG({col_name}) as avg_val FROM {table_name}"
                            numeric_result = sess.execute(text(numeric_query))
                            numeric_stats = numeric_result.fetchone()._asdict()
                            analysis["column_stats"][col_name].update(numeric_stats)
                        except:
                            pass  # Skip if numeric operations fail
            
            return json.dumps(analysis, default=str)
            
        except Exception as e:
            logger.error(f"Error analyzing table: {e}")
            return f"Error analyzing table: {e}"

    def get_db_size(self) -> str:
        """Get database size information.

        Returns:
            str: Database size information.
        """
        try:
            log_debug("Getting database size information")
            
            # This query works for many databases but may need adjustment for specific ones
            size_queries = {
                "postgresql": "SELECT pg_size_pretty(pg_database_size(current_database())) as size",
                "mysql": "SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) AS size_mb FROM information_schema.tables WHERE table_schema = DATABASE()",
                "sqlite": "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()",
                "mssql": "SELECT SUM(size) * 8 / 1024 AS size_mb FROM sys.master_files WHERE database_id = DB_ID()"
            }
            
            dialect_name = self.db_engine.dialect.name.lower()
            
            if dialect_name in size_queries:
                with self.Session() as sess:
                    result = sess.execute(text(size_queries[dialect_name]))
                    size_info = result.fetchone()._asdict()
                    return json.dumps({"database_size": size_info})
            else:
                return json.dumps({"database_size": "Size information not available for this database type"})
                
        except Exception as e:
            logger.error(f"Error getting database size: {e}")
            return f"Error getting database size: {e}"

    def list_views(self) -> str:
        """List all views in the database.

        Returns:
            str: JSON list of views.
        """
        try:
            log_debug("Listing views in the database")
            
            inspector = inspect(self.db_engine)
            view_names = inspector.get_view_names(schema=self.schema)
            
            return json.dumps(view_names)
            
        except Exception as e:
            logger.error(f"Error listing views: {e}")
            return f"Error listing views: {e}"

    def list_indexes(self, table_name: Optional[str] = None) -> str:
        """List indexes in the database or for a specific table.

        Args:
            table_name (Optional[str]): If provided, list indexes for this table only.

        Returns:
            str: JSON list of indexes.
        """
        try:
            log_debug(f"Listing indexes for table: {table_name if table_name else 'all tables'}")
            
            inspector = inspect(self.db_engine)
            
            if table_name:
                indexes = inspector.get_indexes(table_name, schema=self.schema)
                return json.dumps({table_name: indexes})
            else:
                all_indexes = {}
                table_names = inspector.get_table_names(schema=self.schema)
                for table in table_names:
                    try:
                        indexes = inspector.get_indexes(table, schema=self.schema)
                        if indexes:
                            all_indexes[table] = indexes
                    except:
                        continue  # Skip tables that can't be inspected
                
                return json.dumps(all_indexes)
                
        except Exception as e:
            logger.error(f"Error listing indexes: {e}")
            return f"Error listing indexes: {e}"

    def get_foreign_keys(self, table_name: str) -> str:
        """Get foreign key information for a table.

        Args:
            table_name (str): Name of the table.

        Returns:
            str: JSON string with foreign key information.
        """
        try:
            log_debug(f"Getting foreign keys for table: {table_name}")
            
            inspector = inspect(self.db_engine)
            foreign_keys = inspector.get_foreign_keys(table_name, schema=self.schema)
            
            return json.dumps(foreign_keys)
            
        except Exception as e:
            logger.error(f"Error getting foreign keys: {e}")
            return f"Error getting foreign keys: {e}"

    def get_primary_keys(self, table_name: str) -> str:
        """Get primary key information for a table.

        Args:
            table_name (str): Name of the table.

        Returns:
            str: JSON string with primary key information.
        """
        try:
            log_debug(f"Getting primary keys for table: {table_name}")
            
            inspector = inspect(self.db_engine)
            primary_keys = inspector.get_pk_constraint(table_name, schema=self.schema)
            
            return json.dumps(primary_keys)
            
        except Exception as e:
            logger.error(f"Error getting primary keys: {e}")
            return f"Error getting primary keys: {e}"

    def execute_transaction(self, queries: List[str]) -> str:
        """Execute multiple SQL statements in a single transaction.

        Args:
            queries (List[str]): List of SQL queries to execute in transaction.

        Returns:
            str: Success message or error details.
        """
        try:
            log_debug(f"Executing transaction with {len(queries)} queries")
            
            with self.Session() as sess, sess.begin():
                results = []
                for i, query in enumerate(queries):
                    result = sess.execute(text(query))
                    results.append(f"Query {i+1}: {result.rowcount} rows affected")
                
            return f"Transaction completed successfully. {'; '.join(results)}"
            
        except Exception as e:
            logger.error(f"Error executing transaction: {e}")
            return f"Error executing transaction: {e}"

    def get_table_size(self, table_name: str) -> str:
        """Get size information for a specific table.

        Args:
            table_name (str): Name of the table.

        Returns:
            str: Table size information.
        """
        try:
            log_debug(f"Getting size for table: {table_name}")
            
            dialect_name = self.db_engine.dialect.name.lower()
            
            size_queries = {
                "postgresql": f"""
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('{table_name}')) as total_size,
                        pg_size_pretty(pg_relation_size('{table_name}')) as table_size,
                        pg_size_pretty(pg_total_relation_size('{table_name}') - pg_relation_size('{table_name}')) as index_size
                """,
                "mysql": f"""
                    SELECT 
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS total_size_mb,
                        ROUND((data_length / 1024 / 1024), 2) AS table_size_mb,
                        ROUND((index_length / 1024 / 1024), 2) AS index_size_mb
                    FROM information_schema.TABLES 
                    WHERE table_name = '{table_name}' AND table_schema = DATABASE()
                """,
                "sqlite": f"SELECT COUNT(*) * 1024 as approximate_size FROM {table_name}"
            }
            
            if dialect_name in size_queries:
                with self.Session() as sess:
                    result = sess.execute(text(size_queries[dialect_name]))
                    size_info = result.fetchone()._asdict() if result else {}
                    return json.dumps({"table_name": table_name, "size_info": size_info}, default=str)
            else:
                return json.dumps({"table_name": table_name, "size_info": "Size information not available for this database type"})
                
        except Exception as e:
            logger.error(f"Error getting table size: {e}")
            return f"Error getting table size: {e}"

    def vacuum_analyze(self, table_name: Optional[str] = None) -> str:
        """Perform database maintenance operations (VACUUM/ANALYZE).

        Args:
            table_name (Optional[str]): Table to analyze. If None, analyzes entire database.

        Returns:
            str: Success or error message.
        """
        try:
            dialect_name = self.db_engine.dialect.name.lower()
            
            if dialect_name == "postgresql":
                if table_name:
                    query = f"VACUUM ANALYZE {table_name}"
                else:
                    query = "VACUUM ANALYZE"
            elif dialect_name == "sqlite":
                if table_name:
                    query = f"ANALYZE {table_name}"
                else:
                    query = "VACUUM; ANALYZE"
            else:
                return f"VACUUM/ANALYZE not supported for {dialect_name}"
            
            log_debug(f"Running maintenance: {query}")
            
            with self.Session() as sess, sess.begin():
                sess.execute(text(query))
                
            return f"Maintenance completed successfully for {table_name if table_name else 'database'}"
            
        except Exception as e:
            logger.error(f"Error during maintenance: {e}")
            return f"Error during maintenance: {e}"

    def get_query_plan(self, query: str) -> str:
        """Get the execution plan for a SQL query.

        Args:
            query (str): SQL query to analyze.

        Returns:
            str: Query execution plan.
        """
        try:
            log_debug(f"Getting query plan for: {query}")
            
            dialect_name = self.db_engine.dialect.name.lower()
            
            if dialect_name == "postgresql":
                explain_query = f"EXPLAIN (FORMAT JSON) {query}"
            elif dialect_name == "mysql":
                explain_query = f"EXPLAIN FORMAT=JSON {query}"
            elif dialect_name == "sqlite":
                explain_query = f"EXPLAIN QUERY PLAN {query}"
            else:
                explain_query = f"EXPLAIN {query}"
            
            with self.Session() as sess:
                result = sess.execute(text(explain_query))
                plan = result.fetchall()
                plan_data = [row._asdict() for row in plan]
                
            return json.dumps({"query": query, "execution_plan": plan_data}, default=str)
            
        except Exception as e:
            logger.error(f"Error getting query plan: {e}")
            return f"Error getting query plan: {e}"

    def duplicate_table_structure(self, source_table: str, target_table: str, copy_data: bool = False) -> str:
        """Create a new table with the same structure as an existing table.

        Args:
            source_table (str): Name of the source table to copy structure from.
            target_table (str): Name of the new table to create.
            copy_data (bool): Whether to copy data as well. Defaults to False.

        Returns:
            str: Success or error message.
        """
        try:
            log_debug(f"Duplicating table structure from {source_table} to {target_table}")
            
            dialect_name = self.db_engine.dialect.name.lower()
            
            if copy_data:
                if dialect_name in ["postgresql", "mysql"]:
                    query = f"CREATE TABLE {target_table} AS SELECT * FROM {source_table}"
                elif dialect_name == "sqlite":
                    query = f"CREATE TABLE {target_table} AS SELECT * FROM {source_table}"
                else:
                    query = f"SELECT * INTO {target_table} FROM {source_table}"
            else:
                if dialect_name == "postgresql":
                    query = f"CREATE TABLE {target_table} (LIKE {source_table} INCLUDING ALL)"
                elif dialect_name == "mysql":
                    query = f"CREATE TABLE {target_table} LIKE {source_table}"
                elif dialect_name == "sqlite":
                    query = f"CREATE TABLE {target_table} AS SELECT * FROM {source_table} WHERE 1=0"
                else:
                    # Generic approach - get structure and recreate
                    inspector = inspect(self.db_engine)
                    columns = inspector.get_columns(source_table, schema=self.schema)
                    
                    column_defs = []
                    for col in columns:
                        col_def = f"{col['name']} {col['type']}"
                        if not col['nullable']:
                            col_def += " NOT NULL"
                        if col.get('default'):
                            col_def += f" DEFAULT {col['default']}"
                        column_defs.append(col_def)
                    
                    query = f"CREATE TABLE {target_table} ({', '.join(column_defs)})"
            
            with self.Session() as sess, sess.begin():
                sess.execute(text(query))
                
            action = "copied with data" if copy_data else "structure copied"
            return f"Table '{target_table}' created successfully - {action} from '{source_table}'."
            
        except Exception as e:
            logger.error(f"Error duplicating table: {e}")
            return f"Error duplicating table: {e}"

