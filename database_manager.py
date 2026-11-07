import sqlite3
from pathlib import Path

DATABASE = Path(__file__).resolve().parent / "nextgen.db"

def get_tables(cursor):
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
    """)
    return [table[0] for table in cursor.fetchall()]

def manage_table(cursor, connection, table_name):
    while True:
        print(f"\n--- Managing {table_name.title()} ---")
        print("1. View all records")
        print("2. Delete a record")
        print("3. Clear all records")
        print("4. Back to Main Menu")
        choice = input("\nEnter your choice (1/2/3/4): ")
        if choice == "1":
            cursor.execute(f'SELECT * FROM "{table_name}"')
            records = cursor.fetchall()
            if records:
                print(f"\n--- {table_name.title()} Records ---")
                for record in records:
                    print(record)
            else:
                print("\nNo records found.")
        elif choice == "2":
            record_id = input("Enter Record ID to delete: ").strip()
            if not record_id.isdigit():
                print("Please enter a valid numeric ID.")
                continue
            cursor.execute(
                f'DELETE FROM "{table_name}" WHERE id = ?',
                (int(record_id),)
            )
            if cursor.rowcount > 0:
                connection.commit()
                print("Record deleted successfully!")
            else:
                print("No record found with that ID.")
        elif choice == "3":
            confirm = input(
                f"Type YES to delete all records from {table_name}: "
            )
            if confirm == "YES":
                cursor.execute(f'DELETE FROM "{table_name}"')
                cursor.execute(
                    "DELETE FROM sqlite_sequence WHERE name = ?",
                    (table_name,)
                )
                connection.commit()
                print("All records deleted and ID reset!")
            else:
                print("Operation cancelled.")
        elif choice == "4":
            break
        else:
            print("Invalid choice!")

def main():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    try:
        while True:
            tables = get_tables(cursor)
            print("\n--- NextGen Database Manager ---")
            for index, table in enumerate(tables, start=1):
                print(f"{index}. Manage {table.title()}")
            exit_option = len(tables) + 1
            print(f"{exit_option}. Exit")
            choice = input("\nEnter your choice: ")
            try:
                choice = int(choice)
                if 1 <= choice <= len(tables):
                    manage_table(
                        cursor,
                        connection,
                        tables[choice - 1]
                    )
                elif choice == exit_option:
                    print("\nDatabase Manager closed.")
                    break
                else:
                    print("Invalid choice!")
            except ValueError:
                print("Please enter a valid number!")
    finally:
        connection.close()

if __name__ == "__main__":
    main()