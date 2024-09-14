from getpass import getpass
import sqlite3
from datetime import datetime

def connect_to_database(db_path):
    global connection, cursor  # Declare 'connection' and 'cursor' as global variables to use them outside the function.
    connection = sqlite3.connect(db_path)  # Establish a new database connection using the provided database path.
    cursor = connection.cursor()  # Create a cursor object to interact with the database.
    cursor.execute('PRAGMA foreign_keys=ON;')  # Enable SQLite foreign key constraint support for referential integrity.
    connection.commit()  # Commit any changes made by the PRAGMA statement to the database.


def login():
    """Login system for users."""
    print("\nPlease log in:")
    email = input("Email: ")
    pwd = getpass("Password: ") 
    return check_credentials(email, pwd)


def check_credentials(email, pwd):
    """Check if email and pwd are valid for members."""
    # Using parameterized queries to prevent SQL injection
    cursor.execute("SELECT * FROM members WHERE lower(email) = ? AND passwd = ?", (email.lower(), pwd)) # case insensitive
    user = cursor.fetchone()
    if user:
        print("Login successful!\n")
        return user[0]  # Assuming the first column is the email or user identifier
    else:
        print("\nInvalid email or password\n")
        return None


def register():
    """
    Allows unregistered users to sign up by providing a unique email and other details.
    Ensures that the email and name conform to basic validity requirements and that the email hasn't already been registered.
    """
    print("\nRegistration for new users:")

    # Validate the email format
    while True:
        email = input("Enter your email: ").strip()
        # Check if the email contains an '@' with characters before and after it, 
        # and a '.' in the domain part after '@', also ensuring the email is split into exactly two parts by '@'.
        if (email and '@' in email and '.' in email.split('@')[1] and 
                len(email.split('@')) == 2 and
                email.split('@')[0] and email.split('@')[1]):
            break  # Break the loop if the email is valid
        print("Invalid email format. Please enter a valid email with '@' and '.' in the domain part.")

    # Validate the name to ensure it doesn't contain special characters
    while True:
        name = input("Enter your name: ").strip().lower()  # Take the input and convert it to lowercase
        # Define a list of invalid characters to check against
        invalid_chars = ["(", ")", "[", "]", "=", "+", "-", "*", "&", "^", "%", "$", "#", "@", "!"]
        # Check if the name contains any invalid characters
        if name and all(x not in invalid_chars for x in name):
            break  # Break the loop if the name is valid
        print("Invalid name input, please enter a valid name without special characters like '(', ')', '[', ']', '=', '+', '-', '*', '&', '^', '%', '$', '#', '@', '!'.")

    # Prompt for a password with basic validation to ensure it's not empty
    while True:
        pwd = getpass("Enter your password: ").strip()  # Securely capture the password without echoing it
        if pwd:
            break  # Break the loop if a password is entered
        print("Password cannot be left empty.")

    # Optional details: birth year and faculty, allowing for empty inputs
    byear = input("Enter your birth year (optional): ").strip() or None
    faculty = input("Enter your faculty (optional): ").strip().lower() or None  # Convert faculty to lowercase

    # Attempt to insert the new user into the database
    try:
        # Execute the INSERT query with parameters to prevent SQL injection
        cursor.execute("INSERT INTO members (email, name, byear, faculty, passwd) VALUES (?, ?, ?, ?, ?)", 
                       (email, name, byear, faculty, pwd))
        connection.commit()  # Commit the transaction to ensure data is saved
        print("Registration successful!\n")
    except sqlite3.IntegrityError as e:
        # Handle cases where the email is already registered
        print(f"This email is already registered: {email}\n")



#1
def get_member_profile(email):
    """
    Display the member's profile including personal information, previous borrowings,
    current borrowings, overdue borrowings, and penalties.
    """
    # Assuming 'connection' and 'cursor' are database connection and cursor objects defined outside this function
    global connection, cursor
    
    # Fetch and display personal information of a member using their email address
    cursor.execute('SELECT name, email, byear FROM members WHERE email = ?', (email,))
    member_info = cursor.fetchone()  # Retrieve the first (and should be only) result of the query
    if member_info:
        # If a member is found, print their name, email, and birth year
        print(f"Personal Information:\nName: {member_info[0]}\nEmail: {member_info[1]}\nBirth Year: {member_info[2]}\n")
    else:
        # If no member matches the provided email, print a message and exit the function
        print("Member not found.")
        return

    # Calculate and display borrowing counts for the member

    # Count the number of books previously borrowed and returned by the member
    cursor.execute('''
    SELECT COUNT(*) FROM borrowings
    WHERE member = ? AND end_date IS NOT NULL
    ''', (email,))
    previous_borrowings = cursor.fetchone()[0]  # Extract the count from the query result

    # Count the number of books currently borrowed (not yet returned) by the member
    cursor.execute('''
    SELECT COUNT(*) FROM borrowings
    WHERE member = ? AND end_date IS NULL
    ''', (email,))
    current_borrowings = cursor.fetchone()[0]  # Extract the count from the query result

    # Count the number of books that are currently borrowed and overdue
    cursor.execute('''
    SELECT COUNT(*) FROM borrowings
    WHERE member = ? AND end_date IS NULL AND julianday('now') - julianday(start_date) > 20
    ''', (email,))
    overdue_borrowings = cursor.fetchone()[0]  # Extract the count from the query result

    # Print the counts of previous, current, and overdue borrowings
    print(f"Borrowing Counts:\nPrevious Borrowings: {previous_borrowings}\nCurrent Borrowings: {current_borrowings}\nOverdue Borrowings: {overdue_borrowings}\n")

    # Fetch and display penalty information related to unpaid penalties for the member

    # Join the 'penalties' and 'borrowings' tables to find penalties associated with the member's borrowings
    # that have not been fully paid. Calculate the count of such penalties and the total unpaid amount.
    cursor.execute('''
    SELECT COUNT(*), SUM(amount - IFNULL(paid_amount, 0)) AS total_debt
    FROM penalties p
    JOIN borrowings b ON p.bid = b.bid
    WHERE b.member = ? AND amount > IFNULL(paid_amount, 0)
    ''', (email,))
    penalties = cursor.fetchone()  # Retrieve the results: count of unpaid penalties and total debt
    unpaid_penalties_count = penalties[0]  # Extract the count of unpaid penalties
    total_debt = penalties[1] if penalties[1] is not None else 0.0  # Extract the total debt, defaulting to 0 if None

    # Print the count of unpaid penalties and the total unpaid amount
    print(f"Penalty Information:\nNumber of Unpaid Penalties: {unpaid_penalties_count}\nTotal Debt Amount: ${total_debt:.2f}")






#2
def return_book(email):
    print("\nReturning a Book:")
    global connection, cursor  # Accesses the global database connection and cursor for SQL execution

    today = datetime.now().date()  # Gets today's date
    deadline_days = 20  # Sets the borrowing deadline as 20 days from the start date

    # Retrieves borrowing information for the user's currently borrowed books that haven't been returned yet
    cursor.execute('''
    SELECT b.bid, bk.title, b.start_date, 
           (julianday(?) - julianday(b.start_date)) - ? AS overdue_days,
           DATE(julianday(b.start_date) + ?) AS return_deadline
    FROM borrowings b
    JOIN books bk ON b.book_id = bk.book_id
    WHERE b.member = ? AND b.end_date IS NULL''', (today, deadline_days, deadline_days, email,))

    borrowings = cursor.fetchall()  # Fetches all records matching the query
    
    # Checks if there are no books to return and exits if true
    if not borrowings:
        print("You have no books to return.")
        return

    # Lists the user's current borrowings
    print("Current Borrowings:")
    for borrowing in borrowings:
        overdue_days = borrowing[3] if borrowing[3] > 0 else 0  # Calculates overdue days, if any
        # Prints each borrowing's details, including the return deadline
        print(f"Borrowing ID: {borrowing[0]}, Title: {borrowing[1]}, Start Date: {borrowing[2]}, Return Deadline: {borrowing[4]}")

    # Prompts the user to enter the ID of the book they wish to return
    bid = input("Enter the Borrowing ID of the book to return: ")
    selected_borrowing = next((b for b in borrowings if str(b[0]) == bid), None)  # Finds the specified borrowing from the list
    if not selected_borrowing:
        print("Invalid Borrowing ID.")  # Error message for invalid ID
        return
    
    # Updates the borrowing record to set the end_date, marking the book as returned
    cursor.execute('UPDATE borrowings SET end_date = ? WHERE bid = ? AND member = ? AND end_date IS NULL', (today, bid, email.lower(),))
    connection.commit()  # Commits the transaction to the database

    # Calculates overdue days and applies a penalty if the book is returned late
    if overdue_days > 0:
        cursor.execute("SELECT MAX(pid) FROM penalties")  # Retrieves the highest penalty ID
        max_pid_result = cursor.fetchone()
        max_pid = max_pid_result[0] if max_pid_result else 0  # Determines the next penalty ID
        new_pid = max_pid + 1
        
        penalty_amount = overdue_days  # Sets the penalty amount based on overdue days
        # Inserts a new penalty record for the overdue book
        cursor.execute('INSERT INTO penalties (pid, bid, amount, paid_amount) VALUES (?, ?, ?, ?)', (new_pid, bid, penalty_amount, 0,))
        # Informs the user about the applied penalty
        print(f"A penalty of ${penalty_amount:.2f} has been applied for {overdue_days} overdue days.")
    else:
        print("Book returned on time. No penalty applied.") 

    # Offers the user to write a review for the returned book
    review_choice = input("Would you like to write a review for this book? (y/n): ").lower()
    if review_choice == 'y':
        # Collects the user's rating and review text
        while True:
            try:
                rating = int(input("Rating (1-5): "))
                if 1 <= rating <= 5:
                    break
                else:
                    print("Error: Rating must be between 1 and 5.")
            except ValueError:
                print("Error: Please enter a numeric rating between 1 and 5.")

        review_text = input("Review: ")
        rdate = today.strftime('%Y-%m-%d')  # Gets the current date for the review
        
        # Retrieves the book ID associated with the returned book
        cursor.execute('SELECT book_id FROM borrowings WHERE bid = ?', (bid,))
        fetch_result = cursor.fetchone()
        book_id = fetch_result[0] if fetch_result else None

        if book_id:
            # Retrieves the highest review ID to determine the next review ID
            cursor.execute("SELECT MAX(rid) FROM reviews")
            max_rid_result = cursor.fetchone()
            max_rid = max_rid_result[0] if max_rid_result else 0
            new_rid = max_rid + 1

            # Inserts the new review into the database
            cursor.execute('INSERT INTO reviews (rid, book_id, member, rating, rtext, rdate) VALUES (?, ?, ?, ?, ?, ?)', 
                           (new_rid, book_id, email, rating, review_text, rdate,))
            print("Review submitted.")  # Confirms the review submission
            connection.commit()  # Commits the transaction
        else:
            print("Error: Book ID could not be found for this borrowing.") 





#3
def search_and_borrow_books(cursor, email):
    """Allows users to search for books based on a keyword and borrow an available one, with unique bid assignment."""
    
    # Prompt the user for a keyword to find books by title or author
    keyword = input("Enter a keyword to search for books (title or author): ").strip().lower()
    
    # Initialize variables for pagination
    page = 0
    page_size = 5
    
    while True:
        offset = page * page_size  # Calculate offset based on current page
        
        # SQL query to fetch books matching the keyword with pagination
        query = '''
        SELECT * FROM (
            SELECT b.book_id, b.title, b.author, b.pyear,
                   IFNULL(AVG(r.rating), 'N/A') AS avg_rating,  -- Calculate the average rating, default to 'N/A'
                   (CASE WHEN EXISTS(SELECT 1 FROM borrowings WHERE book_id = b.book_id AND end_date IS NULL) THEN 'On borrow' ELSE 'Available' END) AS status,
                   1 AS sort_order  -- Priority for title matches
            FROM books b
            LEFT JOIN reviews r ON b.book_id = r.book_id
            WHERE LOWER(b.title) LIKE ?
            GROUP BY b.book_id

            UNION ALL
            
            SELECT b.book_id, b.title, b.author, b.pyear,
                   IFNULL(AVG(r.rating), 'N/A') AS avg_rating,  -- Calculate the average rating for author matches
                   (CASE WHEN EXISTS(SELECT 1 FROM borrowings WHERE book_id = b.book_id AND end_date IS NULL) THEN 'On borrow' ELSE 'Available' END) AS status,
                   2 AS sort_order  -- Lower priority for author matches
            FROM books b
            LEFT JOIN reviews r ON b.book_id = r.book_id
            WHERE LOWER(b.author) LIKE ? AND LOWER(b.title) NOT LIKE ?
            GROUP BY b.book_id
        ) ORDER BY sort_order, 
                 CASE WHEN sort_order = 1 THEN LOWER(title)  -- Sort title matches by title
                      WHEN sort_order = 2 THEN LOWER(author)  -- Sort author matches by author
                 END
        LIMIT ? OFFSET ?  -- Apply pagination limits
        '''
        
        # Execute the query with formatted keywords for LIKE clauses and pagination parameters
        formatted_keyword = f'%{keyword}%'
        cursor.execute(query, (formatted_keyword, formatted_keyword, formatted_keyword, page_size, offset))
        
        books = cursor.fetchall()  # Fetch all matching books
        
        # Inform the user if no books were found or end pagination
        if not books and page == 0:
            print("No books found with that keyword.")
            return
        elif not books:
            print("No more books found.")
            break

        # Display each book's details fetched from the database
        for book in books:
            print(f"Book ID: {book[0]}, Title: {book[1]}, Author: {book[2]}, Year: {book[3]}, Avg Rating: {book[4]}, Status: {book[5]}")

        if len(books) < page_size or input("Show more results? (yes/no): ").lower() != 'yes':
            break
        page += 1  # Increment page for next set of results, if user chooses to continue

    # After displaying all search results, ask the user if they still want to borrow a book
    while True:  # Keep looping until a valid action is taken (either borrowing a book or deciding not to)
        borrow_decision = input("Would you like to borrow a book? (yes/no): ").lower()
        
        if borrow_decision == 'yes':
            book_id = input("Enter the Book ID of the book you wish to borrow: ").strip()
            
            # Validate if the input is numeric to avoid SQL errors
            if not book_id.isdigit():
                print("Please enter a valid numeric Book ID.")
                continue  # Prompt the user again for a valid book ID
            
            # Check if the selected book is already on loan
            cursor.execute("SELECT COUNT(*) FROM borrowings WHERE book_id = ? AND end_date IS NULL", (book_id,))
            if cursor.fetchone()[0] > 0:
                print("This book is currently on borrow and cannot be borrowed.")  # Notify the user if the book is unavailable
            else:
                # Query the current maximum bid value to ensure uniqueness for the new entry
                cursor.execute("SELECT MAX(bid) FROM borrowings")
                max_bid_row = cursor.fetchone()
                max_bid = max_bid_row[0] if max_bid_row[0] is not None else 0
                
                # Calculate the new bid value by incrementing the current maximum by one
                new_bid = max_bid + 1
                
                # Insert the new borrowing record with the unique bid, user email, and book ID
                today = datetime.today().date()  # Get the current date for the start_date
                cursor.execute("INSERT INTO borrowings (bid, member, book_id, start_date) VALUES (?, ?, ?, ?)", 
                               (new_bid, email, book_id, today))
                
                print(f"You have successfully borrowed the book with borrowing ID: {new_bid}.")  # Confirm the successful borrowing
                break  # Exit the loop after successfully borrowing a book
        elif borrow_decision == 'no':
            break  # Exit the loop if the user decides not to borrow a book
        else:
            print("Invalid input. Please answer with 'yes' or 'no'.")  # Handle invalid responses and prompt again





#4
def pay_penalty(email):
    # Inform the user about the unpaid penalties section
    print("\nYour Unpaid Penalties:")

    # Retrieve all unpaid penalties for the user, ensuring the email check is case-insensitive
    cursor.execute('''
        SELECT pid, bid, amount, COALESCE(paid_amount, 0) AS paid_amount
        FROM penalties
        WHERE bid IN (SELECT bid FROM borrowings WHERE member = ?) AND COALESCE(paid_amount, 0) < amount
    ''', (email,))

    penalties = cursor.fetchall()

    # If there are no penalties, inform the user and exit the function
    if not penalties:
        print("You have no unpaid penalties.")
        return

    # Display each unpaid penalty's details
    for penalty in penalties:
        unpaid_amount = penalty[2] - penalty[3]  # Calculate the remaining unpaid amount
        print(f"Penalty ID: {penalty[0]}, Borrowing ID: {penalty[1]}, Unpaid Amount: ${unpaid_amount:.2f}")

    # Ask the user to select a penalty ID for payment or exit
    pid = input("Enter the Penalty ID of the penalty you wish to pay or 'exit' to go back: ")
    if pid.lower() == 'exit':
        return

    # Find the selected penalty from the fetched penalties list
    selected_penalty = next((p for p in penalties if str(p[0]) == pid), None)
    if not selected_penalty:
        print("Invalid Penalty ID.")
        return

    # Prompt the user to enter an amount to pay towards the selected penalty
    while True:
        try:
            payment = float(input(f"Enter the amount you wish to pay towards Penalty ID {pid} (Unpaid Amount: ${unpaid_amount:.2f}): "))
            if 0 < payment <= unpaid_amount:
                break
            else:
                print("Please enter a valid amount within the unpaid amount.")
        except ValueError:
            print("Please enter a numerical value.")

    # Update the penalty record with the new payment amount
    new_paid_amount = selected_penalty[3] + payment
    cursor.execute('''
        UPDATE penalties
        SET paid_amount = ?
        WHERE pid = ?
    ''', (new_paid_amount, pid))

    # Commit the changes to the database
    connection.commit()

    # Inform the user of the successful payment and the remaining unpaid amount
    print(f"You have paid ${payment:.2f} towards Penalty ID {pid}. Remaining Unpaid Amount: ${unpaid_amount - payment:.2f}")

    # Recalculate and display the updated total debt amount for user feedback
    cursor.execute('''
        SELECT SUM(amount - COALESCE(paid_amount, 0))
        FROM penalties
        WHERE bid IN (SELECT bid FROM borrowings WHERE member = ?)
    ''', (email,))
    updated_total_debt = cursor.fetchone()[0] or 0.0
    print(f"Your updated total debt amount: ${updated_total_debt:.2f}")


    
def main():
    if len(sys.argv) != 2:
        print("Usage: python your_script.py <dbname>")
        sys.exit(1)

    db_path = sys.argv[1]

    connect_to_database(db_path)  # Call the function to establish a connection to the specified SQLite database.
    user_email = None  # Initially, no user is logged in.

    while True:
        if user_email:  # If a user is logged in
            user_option = input("Select an option: \n1. View Profile\n2. Return a Book\n3. Search and Borrow Books\n4. Pay a Penalty\n5. Log out\n6. Exit Program\nChoose an option: ")
            if user_option == "1":
                get_member_profile(user_email)
            elif user_option == "2":
                return_book(user_email)  # Return a book
            elif user_option == "3":
                search_and_borrow_books(cursor, user_email) # Search and possibly borrow books
            elif user_option == "4":
                pay_penalty(user_email)  # Pay a penalty
            elif user_option == "5":
                print("You have been logged out.")
                user_email = None  # Reset the user session
            elif user_option == "6":
                print("Exiting program.")
                break  # Exit the program
            else:
                print("Invalid choice. Please try again.")
        else:  # If no user is logged in
            option = input("Welcome to the Library System!\n1. Log In\n2. Register\n3. Exit\nChoose an option: ")
            if option == "1":
                user_email = login()
                if user_email:
                    print(f"Welcome, {user_email}! What would you like to do next?\n")
            elif option == "2":
                register()
            elif option == "3":
                print("Exiting program.")
                break  # Exit the program
            else:
                print("Invalid choice. Please try again.\n")
    
    connection.close()

if __name__ == "__main__":
    main()