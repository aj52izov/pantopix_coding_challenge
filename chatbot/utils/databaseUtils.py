import traceback
import logging
from sqlalchemy import Table, Column, JSON, TIMESTAMP, MetaData, func, String, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError
from utils.config import get_db_host, get_db_name, get_db_password, get_db_port, get_db_username, get_schema_name, get_table_name

# Set up logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseInteraction:
    """DatabaseInteraction handles asynchronous database operations."""

    def __init__(self, username: str = get_db_username(), 
                 password: str = get_db_password(), 
                 host: str = get_db_host(),
                 schema = get_schema_name(), 
                 port: int = get_db_port(), 
                 db_name: str = get_db_name(), 
                 table_name: str = get_table_name(envKey="CHATBOT_LOG"),
                 columns_dict: dict = {
                     "id": {"type": String, "primary_key": True}, 
                     "data": {"type": JSON}, 
                     "conversation": {"type": JSON},
                 },
                 extra_cols: dict = {},
                 pool_size=10,
                 max_overflow=20,
                 pool_timeout=60,
                 pool_recycle=1800,
                 pool_pre_ping=True):
        # Construct the database URL
        if port:
            self.__database_url = f'postgresql+asyncpg://{username}:{password}@{host}:{port}/{db_name}'
        else:
            self.__database_url = f'postgresql+asyncpg://{username}:{password}@{host}/{db_name}'
        
        # Create an asynchronous SQLAlchemy engine
        self.__engine = create_async_engine(
            self.__database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping
        )
        
        self.__metadata = MetaData()
        
        # Update the columns dictionary with any extra columns
        if extra_cols:
            columns_dict.update(extra_cols)
            
        self._columns_dict = columns_dict
        
        # Define columns for the table
        columns = [
            Column(name=key, 
                   type_=value["type"], 
                   primary_key=value.get("primary_key", False), 
                   nullable=value.get("nullable", False)) 
            for key, value in columns_dict.items()
        ]
        
        # Add a created_at timestamp column
        columns.append(Column('created_at', TIMESTAMP(timezone=True), server_default=func.now()))
        
        # Define the table schema
        self.__table = Table(table_name, self.__metadata,
                             *columns,
                             schema=schema,
                             extend_existing=True)
                             
        # Create a session local factory
        self.__AsyncSessionLocal = sessionmaker(bind=self.__engine, class_=AsyncSession)

    async def __maybe_add_columns(self):
        """Check if any specified columns are missing in the database and add them."""
        table_name = self.__table.name
        schema = self.__table.schema
        sync_engine = create_engine(self.__database_url.replace("+asyncpg", ""))
        insp = inspect(sync_engine)
        
        # Get the existing columns in the database
        existing_cols = {col['name'] for col in insp.get_columns(table_name, schema=schema)}
        to_add = []
        
        # Identify columns to add
        for col, param in self._columns_dict.items():
            if col not in existing_cols:
                col_type = param['type']().compile(sync_engine.dialect)
                nullable = "" if param.get("nullable", True) else " NOT NULL"
                to_add.append(f'ADD COLUMN "{col}" {col_type}{nullable}')
        
        # Execute the ALTER TABLE statement if there are new columns
        if to_add:
            stmt = f'ALTER TABLE "{schema}"."{table_name}" ' + ", ".join(to_add)
            async with self.__engine.begin() as conn:
                await conn.execute(text(stmt))
            logger.info(f"Added columns: {to_add}")
        
    async def dispose(self):
        """Dispose the database engine."""
        await self.__engine.dispose()
        logger.info("Database engine disposed.")
    
    async def create_tables(self):
        """Create the database table if it does not already exist."""
        async with self.__engine.begin() as conn:
            await conn.run_sync(self.__metadata.create_all)
        await self.__maybe_add_columns()
        logger.info("Tables created or updated in the database.")

    async def insert_data(self, column_values: dict):
        """Insert new data into the table.
        
        Args:
            column_values: dict - A dictionary of column names and their corresponding values.
        """
        try:
            async with self.__AsyncSessionLocal() as session:
                insert_stmt = self.__table.insert().values(column_values)
                await session.execute(insert_stmt)
                await session.commit()
                logger.info(f"Inserted data: {column_values}")
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemyError occurred during insertion: {e}")
            logger.error(traceback.format_exc())

    async def update_data(self, id: str, column_values: dict):
        """Update existing data in the table identified by its ID.
        
        Args:
            id: str - The unique identifier of the row to update.
            column_values: dict - The values to update in the row.
        """
        try:
            async with self.__AsyncSessionLocal() as session:
                update_stmt = self.__table.update().where(self.__table.c.id == id).values(column_values)
                await session.execute(update_stmt)
                await session.commit()
                logger.info(f"Updated data for ID: {id} with values: {column_values}")
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemyError occurred during update: {e}")
            logger.error(traceback.format_exc())

    async def get_data(self, id: str | int):
        """Fetch data from the table by ID.
        
        Args:
            id: str | int - The unique identifier of the row to fetch.
        
        Returns:
            The fetched row or None if not found.
        """
        try:
            async with self.__AsyncSessionLocal() as session:
                select_stmt = self.__table.select().where(self.__table.c.id == id)
                result = await session.execute(select_stmt)
                result = result.fetchone()
                logger.info(f"Fetched data for ID: {id} - Result: {result}")
                return result  # Returning the JSON data
        except OperationalError as e:
            logger.error(f"OperationalError occurred: {e}")
        except ProgrammingError as e:
            logger.error(f"ProgrammingError occurred: {e}")
        
        return None
        
    async def inspect_table_existence(self, schema, table_name):
        """Check if a table exists in the specified schema.
        
        Args:
            schema: str - Schema in which to check for the table.
            table_name: str - Name of the table to check.
        
        Returns:
            bool - True if the table exists, otherwise False.
        """
        async with self.__engine.begin() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names(schema=schema)
            )
            logger.info(f"All tables in schema '{schema}': {tables}")
            exists = table_name in tables
            logger.info(f"Table {table_name} existence check: {exists}")
            return exists

    async def add_columns(self, columns_dict: dict):
        """Add new columns to the existing table.
        
        Args:
            columns_dict: dict - A dictionary of columns to be added.
        """        
        try:
            async with self.__AsyncSessionLocal() as session:
                for key, value in columns_dict.items():
                    col_type = value["type"]
                    col_type_dialect = col_type.compile(dialect=self.__engine.dialect)  # Convert class to type
                    sql_query = text(f"""ALTER TABLE {self.__table.name} ADD COLUMN {key} {col_type_dialect};""")
                    await session.execute(sql_query)
                    await session.commit()
                    logger.info(f"Column {key} added!")
        except TypeError as e:
            logger.error(f"Type Error for column {key}: {e}")
        except ArgumentError as e:
            logger.error(f"Column {key} already exists: {e}")