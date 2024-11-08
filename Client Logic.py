import socket 
import re
import json
import hashlib
import threading
import time

#Global Vars
response_received = threading.Event() # to prevent interleaving
print_lock = threading.Lock() 
msg_count = 0 # keep track of new msgs

def createSocket():
    '''creating new socket'''
    client= socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    client.connect((socket.gethostbyname(socket.gethostname()), 1235))
    return client


#VALIDATION AND HASHING
def validatePassword():
    '''Checks if password meets conditions'''
    while True:
        password = input("Create password (must be at least 8 characters and include a capital letter):\n").strip()
        if len(password) >= 8 and any(c.isupper() for c in password): # at least one upper and more than 8
            return password
        else:
            print("Password must be at least 8 characters long and include at least one uppercase letter.")
            continue
        
        
def validatename():
     '''Checks if name meets conditions'''
     while True:
         name= input("Enter your name:\n").strip()
         if name==" ":
             print("Invalid name format, please try again.")
         else:
             return name 
        
        
def validateusername():
     '''Checks if username meets conditions'''
     while True:
         username= input("Enter your username:\n").lower().strip()
         if len(username)==0:
             print("Invalid username format, please try again.")  
         else:
             return username 
        
def hash_password(password): 
    '''encrypts the password for user safety'''
    hash_object = hashlib.sha256()
    hash_object.update(password.encode('utf-8'))
    return hash_object.hexdigest()


def validateEmail():
    '''Check if email is valid in aub email format'''
    while True:
        email = input("Enter your email address\n").lower().strip()
        if len(email) != 0:
            if re.match(r"[^@]+@mail\.aub\.edu$", email): #regex to validate
                return email
            else:
                print("Invalid email format, please try again.")
        else:
            print("Invalid email format, please try again.")
#VALIDATION AND HASHING END


#LOG IN REGISTER
def logOrReg(client):  
    while True:
        message=client.recv(1024).decode('utf-8')
        print(message)
        choice = input("register/log in: ").lower()
        print()
        client.send(choice.encode('utf-8'))
        
        if choice.lower()=='register':
            register(client)
            msg = client.recv(1024).decode('utf-8') #either created or failed
            if msg == "Account created. Please log in with your new account.":
                print(msg)
                print()
                response = login(client)
                if "login successful." in response:
                    break
                else:
                    print(response)
                    continue
            else:
                print(msg)
                continue ##repeat loop
        elif choice.lower()=="log in":
            response = login(client)
            if "login successful." in response:
                break
            else:
                print(response)
                continue
        else:
            print("INVALID CHOICE")
            '''make sure server side resends msg for login and reg'''
            
            
def register(client):
    '''user reg, if username is taken ask user to try a diff one'''
    print("Register a new account")
    name = validatename() #
    print()
    email = validateEmail()
    print()
    username = validateusername().strip() 
    print()
    password = validatePassword()
    hashed_password = hash_password(password)
    print()
    client.send(name.encode('utf-8'))
    client.send(email.encode('utf-8'))
    client.send(username.encode('utf-8'))
    client.send(hashed_password.encode('utf-8'))
    print()


def login(client): 
    '''user login'''

    print("Log in to your account")
    username = input("Enter username:\n").strip()
    print()
    password = input("Enter password:\n")
    hashed_password = hash_password(password)

    # Send login details to server
    client.send(username.encode('utf-8'))  
    client.send(hashed_password.encode('utf-8'))
    response = client.recv(1024).decode('utf-8')
    if "login successful." in response:
        print(response)

    return response


#LOG IN REGISTER END
    
        
#COMMUNICATION WITH SERVER USING JSON
def send_req(client, req):
    '''send request to server in json format'''
    request = json.dumps(req)
    client.send(request.encode())
        
    
#ALL HELPER FUNCTIONS    
def add_product_to_marketplace(client):
    '''adds product for selling'''
    name_of_product=input("Enter product name :\n" )
    while True:
        price = input("Enter product price:\n")
        try:
            price = float(price)
            break
        except ValueError:
            print("Price has to be a number!")
    description=input("Enter product description :\n" )
    image_path=input("Enter image file path :\n" )
    req = {"action" : "add" , "name" : name_of_product, #send product info to server
         "price" : price, 
         "description" : description, 
         "image" : image_path
         }
    send_req(client, req)
    
    
def handle_display_user(client, user):
    req = {"action" : "display_user", "username" : user}
    send_req(client, req)

    
def handle_display_all(client):
    request = {"action" : "display_all"}
    send_req(client, request)
    
    
def handle_search(client, search_term):
    '''handles searching process'''
    req = {"action" : "show_matching", "search_term" : search_term}
    send_req(client, req)


def handle_buy(client, reply):
    '''handles buying item'''
    product_list = reply["message"]
    product_ids = reply["IDs"]
    print(product_list)
    ID = input("Enter ID of product you want to buy or type 'exit' to return: ") # asks user for id 
    if ID in product_ids:
        send_req(client, {"action" : "buy" , "prod_list" : product_list, "ID" : ID}) # sends buy request
        print("sent")
    else:
        print("Product not found.")
        response_received.set()
        

def handle_view(client, choice):
    '''handle viewing past buyers'''
    client.send(choice.encode('utf-8'))
    req = {"action" : "view"}
    send_req(client, req)
        

def handle_get_messages(client):
    '''handle getting new msgs'''
    req = {"action": "get_msgs"}
    send_req(client, req)   
    

def handle_send_msg(client, choice):
    '''handles sending msg to user'''
    parts = choice.split(" ", 2)
    if len(parts) == 3: #if right format send msg to server with details
        to_user = parts[1]
        message = parts[2]
        req = {"action": "send", "to_user": to_user, "message": message}
        send_req(client, req)
    else:
        print("Invalid send msg format, please use send <user> <msg>") #if wrong format stop
        response_received.set()
        
        
def handle_check_user(client, user):
    '''Checks if user is online'''
    req = {"action" : "check", "user" : user}
    send_req(client, req)
    
    
def log_out(client):
    '''logs user out of server'''
    request = {"action" : "log_out"}
    send_req(client, request)
    
    
def handle_help():
    print("\nList of commands:", end ="\n\n")
    print("add: Sell items on market", end ="\n\n")
    print("buy <item>: Display all 'item's to buy from market", end ="\n\n")
    print("display: Displays all items for sale", end ="\n\n")
    print("display <username>: Displays all products of 'username'", end ="\n\n")
    print("view: shows all past buyers of your products", end ="\n\n")
    print("check <user>: Checks if 'user' is online to message them.", end ="\n\n")
    print("send <user> <msg>: sends 'user' a 'msg' if 'user' is online", end ="\n\n")
    print("messages: Shows new messages from other users", end ="\n\n")
    print("refresh: Refreshes the page", end ="\n\n")
    print("exit: log out", end ="\n\n\n")
    response_received.set()



# def receive_data(client): #might implement later for recieving big amounts of data
#     full_data = b''
#     while True:
#         chunk = client.recv(1024)
#         if b'END_OF_PRODUCTS' in chunk:
#             # Remove the end marker and add the data before breaking
#             full_data += chunk.replace(b'END_OF_PRODUCTS', b'')
#             break
#         full_data += chunk
#     return full_data.decode('utf-8')


#HELPER FUNCTIONS END    
    

        
        
def receive_thread(client):
    """Thread to handle receiving messages from the server."""
    global inFunc
    global msg_count
    while True:
        try:
            reply = client.recv(1024).decode()
            reply = json.loads(reply)
            action = reply["action"]

            with print_lock:
                if action=="display_all":
                    print(reply["content"], end = '\n\n')
                    response_received.set()
                    
                elif action=="display_user":
                    print(reply["content"], end ="\n\n")
                    response_received.set()

                elif action == "get_msgs" and reply["new"]:
                    msg_count = 0
                    print(reply["content"])
                    response_received.set()

                elif action == "log_out":
                    print("logging out")
                    break
                
                elif action == "new_message":
                    msg_count += 1
                    response_received.set()
                    
                elif action == "matching_prods":
                    '''displays matching products'''
                    handle_buy(client, reply)
                    
                        
                elif action == "message":
                    print(reply["message"])
                    response_received.set()

        except:
            break
        

def driver(client):
    '''Main driver code for client'''
    global msg_count
    while True:
        response_received.wait()#wait  to recieve response from server before asking for next input
        response_received.clear()

        with print_lock: # to prevent interleaving
            print("\nType your command or type help for a list of commands.", end = ' ')
            if msg_count==1:
                print("You have 1 new message.", end = '\n')
            elif msg_count>1:
                print(f"You have {msg_count} new messages", end =  '\n')
            else:
                print()
            choice = input().lower()
            if len(choice.split())==1 and choice == "help":
                handle_help() 
            elif len(choice.split())== 1 and choice == "messages":
                msg_count = 0
                handle_get_messages(client)
            elif len(choice.split())==1 and choice == "add":
                add_product_to_marketplace(client)
            elif len(choice.split())==1 and choice == "display": #done
                handle_display_all(client)
            elif choice.startswith('display'): #done
                '''display all items for sale of specific user'''
                handle_display_user(client, choice.split(' ', 1)[1])
            elif len(choice.split())==1 and choice == "view": 
                '''view all past buyers'''
                handle_view(client, choice)
            elif len(choice.split())==1 and choice == "refresh":
                '''just refresh the driver to load any new messages'''
                print("Refreshing...")
                response_received.set()
                pass 
            elif choice.startswith("buy"):
                '''initiates buying process'''
                search_term = choice.split(' ', 1)[1]
                handle_search(client,search_term)
            elif choice.startswith('check'): #done
                '''checks if user is online'''
                handle_check_user(client, choice.split(' ', 1)[1])
            elif choice.startswith('send'): #done
                '''Send a message to another user'''
                handle_send_msg(client, choice)
            elif len(choice.split())==1 and choice == "exit": 
                '''logs out'''
                log_out(client)
                break
            else:
                print("INVALID INPUT! Type help for a list of supported commands.", flush = True)
                response_received.set()
        time.sleep(0.1) # to prevent overloading 
        
        
#MAIN CODE
def main():
    client = createSocket() #create socket

    try:

        logOrReg(client) #log in or reg
        receiver = threading.Thread(target=receive_thread, args=(client,)) # start thread parallel to driver that terminates with main
        receiver.daemon = True  
        receiver.start()
        
        driver(client) # start driver

    except Exception as e:
        print("Server is shutting down", e)
    finally:
        client.close()
        
    
#---START MAIN---
main()
