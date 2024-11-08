import socket 
import sqlite3   ##count for data base of sellers when client buy count =0
import threading
from datetime import datetime,timedelta
import json
import hashlib
import time

Connections = {}
UserToSocket = {}


message_list = "\nYour messages:\n"

def create_socket():
    '''creates socket for client to bind'''
    server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server.bind((socket.gethostname(), 1235))
    server.listen(5)
    print("Server is listening...")
    return server
    
    
def create_database():
    '''creating necessary database'''
    with sqlite3.connect("AUBoutique.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS userInfo(
                            email text, 
                            password text, 
                            username text, 
                            name text)
                       ''')
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS objForSell(
                            name_of_product text, 
                            username text,
                            price REAL,
                            description TEXT,
                            image_path TEXT, 
                            product_id INTEGER PRIMARY KEY AUTOINCREMENT)
                       ''')
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS log(
                            buyer text, 
                            product text, 
                            product_id text, 
                            seller text)
                       ''')
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS messages(
                           from_user TEXT,
                           to_user TEXT,
                           message TEXT,
                           delivered INTEGER DEFAULT 0)
                       ''')
        conn.commit()


def handle_client_log_reg(client_socket):
    '''handles process of registration and logging in'''
    while True :
        client_socket.send("Welcome! Please type \"register\" to register or \"log in\" to log in ".encode('utf-8'))
        choice=client_socket.recv(1024).decode('utf-8')
        if choice == "register":
            if handle_client_reg(client_socket):
                if handle_client_log(client_socket):
                    break
                else:
                    continue
            else: 
                continue
        elif choice =='log in':
            if handle_client_log(client_socket):
                break
            else:
                continue
        else :
            print("INVALID CHOICE")
                
                
def handle_client_reg(client_socket):
    '''handles reg'''
    with sqlite3.connect("AUBoutique.db") as conn:
        cursor = conn.cursor()
        
        name = client_socket.recv(1024).decode('utf-8')
        email = client_socket.recv(1024).decode('utf-8')
        username = client_socket.recv(1024).decode('utf-8')
        hashed_password = client_socket.recv(1024).decode('utf-8')

        if user_exists(username):
            client_socket.send("Username already exists, please try a different username, or log in with your account.".encode('utf-8'))
            return False
        try :
            cursor.execute("INSERT INTO userInfo (name, email, username, password) VALUES (?, ?, ?, ?)", (name, email, username, hashed_password))
            conn.commit()
            client_socket.send("Account created. Please log in with your new account.".encode('utf-8'))
            return True            
        except sqlite3.IntegrityError:
            client_socket.send("Username already exists, please try a different username, or log in with your account.".encode('utf-8'))
            return False


def handle_client_log(client_socket):
    '''handles login'''
    with sqlite3.connect("AUBoutique.db") as conn:
        cursor = conn.cursor()
        username = client_socket.recv(1024).decode('utf-8')
        print(f"username: {username}")
        hashed_password = client_socket.recv(1024).decode('utf-8')
        print(f"password: {hashed_password}") 
        cursor.execute("SELECT * FROM userInfo WHERE username=? AND password=?",(username, hashed_password)) #checks if user pass pair exists
        user=cursor.fetchone()
        if not check_if_online(user): #if user isnt logged in in another place
            if user: #if user,pass exists in database
                client_socket.send("login successful.".encode('utf-8'))
                print()
                display_all_objects(client_socket)
                Connections[client_socket] = username
                UserToSocket[username] = client_socket
                return True
            else :
                client_socket.send("Invalid username or password, please try again or register!".encode('utf-8'))
                return False
        else:
            client_socket.send("User is logged on elsewhere!".encode('utf-8'))
            return False
        
        
def hash_password(password): 
    '''takes care of encryption'''
    hash_object = hashlib.sha256() 
    hash_object.update(password.encode('utf-8')) 
    return hash_object.hexdigest()



        
def check_if_online(username):
    '''checks if user is online'''
    if username in UserToSocket:
        sock = UserToSocket[username]
        return sock in Connections
    
    
def user_exists(user):
    '''checks if user has an account'''
    with sqlite3.connect("AUBoutique.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM userInfo WHERE username=?", (user,))
        return cursor.fetchone() is not None




def send_reply(client_socket, reply):
    '''takes care of communicating with client using json'''
    reply = json.dumps(reply)
    client_socket.send(reply.encode())


'''Adding And Buying'''

def add_product_to_marketplace(client_socket, name, price, desc, path):
    '''adds product to database'''
    with sqlite3.connect("AUBoutique.db") as conn:
        cursor = conn.cursor()
        username = Connections[client_socket]
        cursor.execute("INSERT INTO objForSell(name_of_product,username,price,description,image_path)VALUES(?,?,?,?,?)",(name,username,price,desc,path))
        conn.commit()
        message="Product added successfully"
        reply={"action":"message","message": message}
        send_reply(client_socket, reply)
        
        
def buy_product(client_socket,product_id):
    '''manipulates databses for buying process'''
    with sqlite3.connect("AUBoutique.db") as conn:

        cursor = conn.cursor()
        cursor.execute("SELECT name_of_product, username, price FROM objForSell WHERE product_id=?", (product_id,))
        product=cursor.fetchone()
        if product :
            
            name_of_product = product[0]  
            seller = product[1]            
            buyer = Connections[client_socket] 
            
            cursor.execute("DELETE FROM objForSell WHERE product_id=?",(product_id,))
            cursor.execute("INSERT INTO log(buyer, product, product_id, seller) VALUES (?, ?, ?, ?)", (buyer, name_of_product, product_id, seller))
            conn.commit()
            
            collection_date=(datetime.now()+timedelta(days=7)).strftime("%Y-%m-%d")
            confirmation_message=f"Purchase confirmed! Please collect '{name_of_product}' from the AUB Post Offie on { collection_date}."
            reply={"action":"message","message": confirmation_message}
           
            send_reply(client_socket, reply)
        else:
            print("something happened in buy_product")


def view_buyer(client_socket) :
    '''view buyers of a client's products'''
    try:
        with sqlite3.connect("AUBoutique.db") as conn:
            cursor = conn.cursor()
            seller = Connections.get(client_socket)
            
            if not seller:
                reply = {"action" : "message", "message" : "Seller information not found."}
                send_reply(client_socket, reply)
                return
            
            cursor.execute("SELECT buyer, product, product_id FROM log WHERE seller = ?", (seller,))
            purchase = cursor.fetchall()           
            if purchase:
                purchase_list = "Purchases of your products :\n"
                for buyer, product, product_id in purchase:
                    purchase_list += f"Buyer: {buyer},\nProduct: {product},\nProduct ID: {product_id}\n\n"

            else:
                purchase_list = "No purchases have been made for your products."
            reply = {"action" : "message", "message" : purchase_list}
            send_reply(client_socket, reply)
            
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        message = "An error occurred while accessing purchase data."
        reply = {"action" : "message", "message" : message}
        send_reply(client_socket, reply)
    except Exception as e:
        print(f"General error: {e}")  
        message = "An unexpected error occurred."
        reply = reply = {"action" : "message", "message" : message}
        send_reply(client_socket, reply)


'''Displaying Items'''
def display_products_of_user(client_socket, user):
    '''displays sellables of a specific user'''
    with sqlite3.connect("AUBoutique.db") as conn:
        cursor = conn.cursor()

        if user_exists(user):
            cursor.execute("SELECT * FROM objForSell WHERE username=?", (user,))
            prod_of_user = cursor.fetchall()

            if prod_of_user:
                product_list = f"Product(s) of {user}:\n"
                for x in prod_of_user:
                    product_list += f"Item: {x[0]}, price: {x[2]}, description: {x[3]}, image: {x[4]}, ID: {x[5]}\n\n"
            else:
                product_list = f"{user} has no items for sale right now!"
        else:
            product_list = "Username does not exist!"
        reply = {"action" : "display_user", "content" : product_list}
        send_reply(client_socket, reply)
        # chunk_size = 1024
        # for i in range(0, len(product_list), chunk_size):
        #     chunk = product_list[i:i + chunk_size] 
        #     client_socket.send(chunk.encode('utf-8'))

        # client_socket.send(b'END_OF_PRODUCTS')

    
    
def display_matching_products(client_socket, search_term):
    '''displays item that closely match the serach term'''
    with sqlite3.connect("AUBoutique.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, name_of_product, username FROM objForSell WHERE name_of_product LIKE ?", ('%' + search_term + '%',))
        products = cursor.fetchall()
        product_ids = []
        if products:

            product_list = "Matching Products:\n"
            for product in products:
                product_list += f"ID: {product[0]}, Item: {product[1]}, Owner: {product[2]}\n\n"
                product_ids.append(str(product[0]))
        else:

            product_list = "No products found matching your search."
              
        reply = {"action" : "matching_prods", "message" : product_list, "IDs" : product_ids} #sends a list of matching prods
        send_reply(client_socket, reply)

        
    
def display_all_objects(client_socket):
    '''displays all items currently in market'''
    with sqlite3.connect("AUBoutique.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM objForSell") # select every sellable
        products = cursor.fetchall()
        product_list = ""
        if products:
            product_list = "Product Listings:\n"
            for x in products:
                product_list += f"Item: {x[0]}, owner: {x[1]}, price: {x[2]}, description: {x[3]}, image: {x[4]}, ID: {x[5]}\n\n"
                
        else:
            product_list = "No products for sale at the moment\n"
        reply = {"action" : "display_all", "content" : product_list}
        send_reply(client_socket, reply)



def relay_msg(client_socket, from_user, to_user, message):
    '''adds messages to database'''
    with sqlite3.connect("AUBoutique.db") as conn:
        cursor = conn.cursor()
        if user_exists(to_user):
            if check_if_online(to_user):
                cursor.execute("INSERT INTO messages(from_user, to_user, message, delivered)VALUES(?,?,?,0)", (from_user, to_user, message))
                msg = f"Message sent to {to_user} successfully."
                send_reply(UserToSocket[to_user], {"action" : "new_message"})
            else:
                msg = f"{to_user} is not online, message could not be sent."
        else:
            msg = "User does not exist please make sure you spelled it correctly."
        reply = {"action" : "message", "message" : msg}
        send_reply(client_socket, reply)
            
            
def get_undelivered_messages(client_socket):
    '''Send unread messages to user'''
    global message_list
    username = Connections[client_socket]
    with sqlite3.connect("AUBoutique.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT from_user, message FROM messages WHERE to_user=? AND delivered=0", (username,))
        messages = cursor.fetchall()
        if messages:
            for msg in messages:
                message_list += f"From: {msg[0]}, Message: {msg[1]}\n\n"
            cursor.execute("UPDATE messages SET delivered=1 WHERE to_user=?", (username,))
            conn.commit()
            reply = {"action": "get_msgs", "new" : True, "content": message_list}
            message_list = "\nYour messages:\n"
        else:
            message_list = "No new messages."
            reply = {"action": "message", "message": message_list}
        send_reply(client_socket, reply)        
        
        
#HELPER FUNCTIONS
def handle_send(client_socket, request):
    '''handles sending msgs to other users'''
    from_user = Connections[client_socket]
    recipient = request["to_user"]
    message = request["message"]
    if recipient == from_user:
        reply = {"action" : "message", "message" : "Cannot send messages to yourself."}
        send_reply(client_socket, reply)
    else:
        relay_msg(client_socket, from_user, recipient, message)

            
     
def handle_check(client_socket, user):
    '''checks online status of user'''
    if user_exists(user):
        if check_if_online(user):
            msg = f"{user} is online."
        else:
            msg =f"{user} is not online."
    else:
        msg ="User does not exist please make sure you spelled it correctly."
    reply = {"action" : "message" , "message" : msg}
    send_reply(client_socket, reply)
    
    
def handle_log_out(client_socket):
    '''logs user out'''
    username = Connections.pop(client_socket, None)
    if username in UserToSocket:
        UserToSocket.pop(username)
    client_socket.close() 
#HELPER FUNCTIONS END




       
#---MAIN DRIVER CODE FOR SERVER----
def driver(client_socket):
    try:
        while True:
            request = client_socket.recv(1024).decode()
            if not request:
                break
            try:
                request = json.loads(request)
                action = request["action"]
                if action == "display_all":
                    display_all_objects(client_socket)
                elif action == "display_user":
                    user = request["username"]
                    display_products_of_user(client_socket, user)
                elif action == "send":
                    handle_send(client_socket, request)
                elif action == "show_matching": 
                    display_matching_products(client_socket, request["search_term"])
                elif action == "buy":
                    buy_product(client_socket, request["ID"])
                elif action == "check":
                    user = request["user"]
                    handle_check(client_socket, user)
                elif action == "add":
                    add_product_to_marketplace(client_socket, request["name"], request["price"], request["description"],request["image"])           
                elif action == "view" :
                    view_buyer(client_socket) 
                elif action == "get_msgs":
                    get_undelivered_messages(client_socket)   
                elif action == "log_out":
                    handle_log_out(client_socket)
            except json.JSONDecodeError as e: 
                print(f"JSONDecodeError: {e} - Raw request: {request}") 
                continue
            else:
                time.sleep(1)
    except (ConnectionResetError, ConnectionAbortedError) as e:
        print(f"Connection error with client: {e}")
    finally:
        handle_log_out(client_socket)
        
            
#---HANDLES CLIENTS---
def handle_client(client_socket):
    try:
        handle_client_log_reg(client_socket)
        driver(client_socket)   
    except (ConnectionAbortedError, ConnectionResetError) as e:
        print(f"Connection with client was terminated error: {e}")
    finally:
        handle_log_out(client_socket)
        
        
#---MAIN FUNCTION---
def main():
    create_database()
    server = create_socket()
    try:
        while True:
            client_socket, addr = server.accept()
            print(f"Connect established with ({client_socket}, {addr})")
            threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()
    except KeyboardInterrupt:
        print("Server is shutting down.")
    finally:
        server.close()
        
#START SERVER    
main()
