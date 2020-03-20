import uuid
import Pyro4
import Pyro4.errors
from time import sleep
import sys
import random


class User :
    def __init__(self) :
        #Initialize user contact details for orders
        #Each user is uniquely identifed by an ID
        self.user_id = 0
        self.first_name = ''
        self.last_name = ''
        self.contact_phone = ''
        self.delivery_zip = ''
        self.address = ''
        #Each order placed by the user is uniquely identified with an order number
        self.order_num  = 1
        i = 1
        #Attempt to connect to front-end server
        while i != 5:
            try:
                ns = Pyro4.locateNS()
                self.server = ns.lookup("JH-front-end")
                self.connected_server = Pyro4.Proxy(self.server)
                break
            #If connection attempt failed, retry 5 times at 5 second intervals
            except Pyro4.errors.CommunicationError:
                print("Connection attempt ", i , " of 5")
                print("Front-end server not found; trying again in 5 seconds...")
                sleep(5)
                i += 1
            #If cannot locate name server, exit user program 
            except Pyro4.errors.NamingError:
                print("Front end server could not be found. Start the name server by calling 'pyro4-ns' in the terminal, or initialize the front-end server by typing 'python3 client.py'")
                exit()
            except Pyro4.errors.ConnectionClosedError:
                print("Connection attempt ", i , " of 5")
                print("Front-end server not found; trying again in 5 seconds...")
                sleep(5)
                i += 1

    #Place a new order
    def create_new_order(self) :
        #Assign a unique ID to the current user
        def create_id():
            raw_id = ""
            for i in range(1, 20):
                raw_id += str(random.randint(1,10))
            return int(raw_id)
        #Collect user details; check for empty input
        def update_contact_details():
            self.first_name = input("First name: ")
            while self.first_name == '':
                self.first_name = input("First name must not be empty; please try again: ")
            self.last_name = input("Last name: ")
            while self.last_name == '':
                self.last_name = input("Last name must not be empty; please try again: ")
            #Check that phone number only contains numeric digits and hyphens
            self.contact_phone = input("Contact phone: ")
            while self.contact_phone == '' or all(c not in "0123456789-" for c in self.contact_phone):
                self.contact_phone = input("Contact phone must not be empty and only contain numbers or hyphens (-): ")
            self.delivery_zip = input("Delivery zip code: ")
            while self.delivery_zip == '':
                self.delivery_zip = input("Delivery zip code must not be empty; please try again: ")
            self.address = input("Delivery address: ")
            while self.address == '':
                self.address = input("Delivery address must not be empty; please try again: ")
            #Initialize an empty shopping cart for this order
            self.cart = []
            return 

        #Generate a unique user ID if not already assigned one
        if self.user_id == 0:
            self.user_id = create_id()

        #If the user at specified ID has already placed an order before, prompt to verify contact details already on file 
        if len(self.first_name) != 0 and len(self.last_name) != 0 and len(self.contact_phone) != 0 and len(self.delivery_zip) and len(self.address) != 0:
            print("\nWelcome back to Just Hungry, "+self.first_name+"\n")
            print("These are the current customer details we have on file for your account:\n")
            print("Name: " + self.first_name + ' ' + self.last_name)
            print("Contact Phone: " + self.contact_phone)
            print("Delivery ZIP Code: " + self.delivery_zip)
            print("Delivery Address: " + self.address+"\n")
            #Ask user to verify contact info is correct
            verify = input("Please confirm these are correct: (Y/N)")
            while verify != 'Y' and verify != 'N':
                verify = input("\n Invalid option selected. Please try again: ")
                #If contact details correct, proceed to initialize an empty shopping cart
            if verify == "Y":
                self.cart = []
            elif verify == "N":
                #Else proceed to collect and update user contact info
                print("\nPlease update your contact details: \n")
                update_contact_details()
        #If no user contact details on file, proceed to collect them
        else: 
            print("\nTo create a new order, please provide your contact details: \n")
            update_contact_details()
        #Assemble user details in array
        user_details = [self.first_name,self.last_name,self.contact_phone,self.delivery_zip,self.address]
        #Send request to front-end server to update user details
        response = self.create_request("USER_DETAILS", self.user_id, user_details)
        #User detail verification involves external API call to validate zip code; if the server returns that the zip code is invalid, prompt user for new zip code
        while response == "Invalid delivery zip code." or response == "Zip code validation failed, please try again later." or response == "Failed to perform validation of postal code via external API call." :
            invalid_zip = input("Invalid delivery zip code; please enter a valid zip code or type QUIT to exit: ")
            if invalid_zip == "QUIT":
                #Terminate user connection
                sys.exit(1)
            else:
                self.delivery_zip = invalid_zip
                user_details[3] = invalid_zip
                response = self.create_request("USER_DETAILS", self.user_id, user_details)
        print("\n"+response+"\n")
        
        #Display available products and their associated stock
        product_list = self.create_request("PRODUCT_LIST", self.user_id, '')
        #If product list is empty or request failed, return error message
        if product_list == "Could not retrieve product list, please try again later." or product_list == "Product list is empty, please try again later.":
            print(product_list)
        else:
            products = []
            #Otherwise display list of products and their current price, stock
            print("Current Just Hungry product inventory:\n")
            for item in product_list:
                products.append(item[0])
                if item[1] != 0:
                    print("Product: " +item[0]+ "\t\t\tPrice: "+str(item[2])+"£" + "\t\t\tIn stock: "+str(item[1]))
                else: 
                    print("Product: " +item[0]+ "\t\t\tPrice: "+str(item[2])+"£" + "\t\t\tOut of stock")
        print("\n")
        #Prompt for user to select item from product list
        selected_product = input("Please specify the item you would like to add to your cart: ")
        while selected_product not in products:
            selected_product = input("The specified input is not in the product list; please try again: ")
        #Prompt for quantity of selected item
        quant = input("\nYou have selected "+selected_product+". Please specify a quantity: ")
        #Check that the supplied quantity is an integer
        while True:
            try:
                int(quant)
                while int(quant)<=0:
                    quant = input("Quantity must be an integer greater than 0. Please specify a quantity for " +selected_product+": ")
                break
            except:
                quant = input("Quantity must be an integer greater than 0. Please specify a quantity for " +selected_product+": ")
        self.cart.append([selected_product, int(quant)])
        print("\nAdded "+quant+" "+selected_product+"(s) to cart.")
        
        #Prompt user to add more items to their cart
        more_to_cart = input("\nWould you like to add more products to your cart? (Y/N): ")
        while more_to_cart != "Y" and more_to_cart != "N":
            more_to_cart = input("Invalid option selected, please try again. Would you like to add more products to your cart? (Y/N): ")
        if more_to_cart == "Y":
            while more_to_cart != "N":
                #If user wants to add more items to their cart, retrieve the product list again
                product_list = self.create_request("PRODUCT_LIST", self.user_id, '')
                if product_list == "Could not retrieve product list":
                    print("Could not retrieve product list, please try again later.")
                    #Terminate user connection
                    sys.exit(1)
                else:
                    products = []
                    #Display list of products and their current stock, price
                    print("\nCurrent Just Hungry product inventory:\n")
                    for item in product_list:
                        products.append(item[0])
                        if item[1] != 0:
                            print("Product: " +item[0]+ "\t\t\tPrice: "+str(item[2])+"£" + "\t\t\tIn stock: "+str(item[1]))
                        else: 
                            print("Product: " +item[0]+ "\t\t\tPrice: "+str(item[2])+"£" + "\t\t\tOut of stock")
                    print("\n")
                #Prompt user for item from product list
                selected_product = input("Please specify the item you would like to add to your cart: ")
                while selected_product not in products:
                    selected_product = input("The specified input is not in the product list; please try again: ")
                #Prompt user for quantity of selected item
                quant = input("\nYou have selected "+selected_product+". Please specify a quantity: ")
                #Ensure quantity is an integer
                while True:
                    try:
                        int(quant)
                        while int(quant)<=0:
                            quant = input("Quantity must be an integer greater than 0. Please specify a quantity for " +selected_product+": ")
                        break
                    except:
                        quant = input("Quantity must be an integer greater than 0. Please specify a quantity for " +selected_product+": ")
                #Add item and specified quantity to cart
                already_in_cart = False
                for item in self.cart:
                    if item[0] == selected_product:
                        already_in_cart = True
                        item_position = self.cart.index(item)
                #If this item is already in the cart, only update the extra quantity 
                if already_in_cart == True:
                    self.cart[item_position][1] += int(quant)
                else:
                    self.cart.append([selected_product, int(quant)])
                #Add item and specified quantity to cart
                print("\nAdded "+quant+" "+selected_product+"(s) to cart.")
                more_to_cart = input("\nWould you like to add more products to your cart? (Y/N): ")
                while more_to_cart != "Y" and more_to_cart != "N":
                    more_to_cart = input("Invalid option selected, please try again. Would you like to add more products to your cart? (Y/N): ")    
        
        #Assign an order ID for the current user's shopping cart
        order_id = self.order_num
        #Initialize an array containing order ID, the cart contents, and initialize order status to active
        current_order = [order_id, self.cart, "Active"]
        #Prompt the user to review their final cart before placing the order
        print("\nPlease review your final cart:\n ")
        for entry in self.cart:
            print("Product: " + entry[0] + "\t\t\tQuantity: "+str(entry[1]))
        total_order_cost = self.create_request("ORDER_COST", self.user_id, self.cart)
        print("\nThe total cost of your order is: "+"{0:.2f}".format(total_order_cost)+"£.")
        current_order.append(total_order_cost)
        confirm = input("\nIf you are satisfied with the contents of your cart, confirm to place your order (Y/N): ")
        while confirm != "Y" and confirm != "N":
            confirm = input("\nInvalid option selected, please try again. If you are satisfied with the contents of your cart, confirm to place your order (Y/N): ")
        #If the user does not verify the cart, cancel the order
        if confirm == "N":
            print("\nVoiding order.")
            return 1
        
        #Once user approves their final cart contents, prompt to select a delivery method    
        delivery_options = ["1", "2", "3"]
        print("\nDelivery Options: \n")
        print("     1  -   Within the next 2 hours; 3£")
        print("     2  -   Same day (by midnight today); 1£")
        print("     3  -   Next day; FREE")
        #Parse user input for delivery method
        selected_delivery = input("\nPlease select a delivery method: ")
        while selected_delivery not in delivery_options:
            selected_delivery = input("\nInvalid delivery method selected; please try again: ")
        if selected_delivery == "1":
            current_order.append("Within the next 2 hours")
            #Add 3 to the total cost of their order for shipping charges
            current_order[3] += 3
        elif selected_delivery == "2":
            current_order.append("Same day")
            #Add 1 to the total cost of their order for shipping charges
            current_order[3] += 1
        elif selected_delivery == "3":
            current_order.append("Next day")

        #Prompt the user if they would like to add tips to their order
        tips = input("\nLastly, would you like to add any tips? (Y/N) ")
        while tips != "Y" and tips != "N":
            tips = input("\n Invalid input supplied. Would you like to add any tips? (Y/N) ")
        #If yes, parse user input to ensure that it is an integer or float
        if tips == "Y":
            def is_num(n):
                try:
                    float(n)
                    return True
                except ValueError:
                    return False
            tip_amount = input("\nHow much would you like to tip? ")
            while is_num(tip_amount) == False:
                tip_amount = input("\nPlease supply a numerical amount to tip: ")
            current_order[3] += float(tip_amount)

        #Truncate current order total to 2 decimal places
        current_order[3] = float("{0:.2f}".format(current_order[3]))
        #Place the order
        place_order = self.create_request("PLACE_ORDER", self.user_id, current_order)
        if place_order == "Order placed succesfully. Please pay on delivery.":
            print("\n"+place_order)
            #Increment the user's order number for subsequent order
            self.order_num += 1
        #Server produces custom out-of-stock message if particular items are not available or an error occurred when executing the request
        elif "Could not place order due to low stock of " in place_order:
            print("\n"+place_order)
        elif place_order == "Could not place order. Please try again later.":
            print("\n"+place_order)
        return 0

    #Retrieve the user's existing orders
    def view_orders(self):
        print("\nRetrieving your existing orders...")
        #Send request to server
        response = self.create_request("VIEW_ORDERS", self.user_id, "")
        #If no orders on file for this user, return an error message
        if response == "Could not retrieve any orders for this user." :
            print("\n"+response)
        #Otherwise iterate through orders and print relevant information to the screen
        else:
            if len(response) == 1:
                print("\n"+"No orders found for this user.")
            else:
                print("\n"+"Your existing orders: ")
                i = 0
                for order in response:
                    if i != 0:
                        print("Order ID: "+ str(order[0])+ "\t Status: "+order[2] + "\t\t Delivery Method: "+order[4])
                        print("\n")
                        for entry in order[1]:
                            print("Product: "+entry[0]+"\t\tQuantity: "+str(entry[1]))
                        print("\n")
                        print("Total Order Cost: "+ str(order[3])+"£")
                        print("_____________________________________")
                    i += 1
                    print("\n")
        return 0
	
    #Enable users to cancel existing orders
    def cancel_order(self) :	
            active_order_ids = []
            #Retrieve a list of all active order for this user
            active_orders = self.create_request("VIEW_ACTIVE", self.user_id, '')
            if active_orders == "No active orders for this user.":
                print("\n"+active_orders)
                return
            elif active_orders == "Could not retrieve active orders for this user.":
                print("\n"+active_orders)
                return
            else:
                print("\nYour active orders:\n")
                #Parse server response and print active orders to the screen
                for order in active_orders:
                    active_order_ids.append(str(order[0]))
                    print("Order ID: "+ str(order[0])+ "\t Status: "+order[2]+ "\t\t Delivery Method: "+order[4])
                    print("\n")
                    for entry in order[1]:
                        print("Product: "+entry[0]+"\t\tQuantity: "+str(entry[1]))
                    print("\n")
                    print("Total Order Cost: "+ str(order[3])+"£")   
                    print("_____________________________________")
                    print("\n")
            #User selects order ID they would like to cancel
            to_cancel = input("Please specify the ID of the order you would like to cancel: ")
            #Ensure order ID selected is in the list of active orders
            while to_cancel not in active_order_ids:
                to_cancel = input("Specified order ID not found. Please try again: ")
            #Send request to cancel - update order status to "Cancelled"
            response = self.create_request("CANCEL", self.user_id, to_cancel)
            #Catch and return any errors
            if response == "Error deleting order." :
                print("\n"+response)
            else:
                print("\n"+response)
            return 0
   
    #Close the user connection to front-end server
    def quit(self):
        print("Quitting Just Hungry...")
        return 0 

    #Initialize request to send user input to front-end server
    def create_request(self, request_type, user_id, request_content) :
        data = {'request' : request_type, 'user_id' : user_id, 'user_inp' : request_content}
        i = 1
        #If sending request fails, try again up to 5 times with a 5 second sleeping interval between requests
        while i != 5:
            try:
                #If user requests to exit, close the active connection to front-end server
                if request_type == "EXIT":
                    self.connected_server.user_requests(data)
                    self.connected_server.shutdown()
                    self.connected_server._pyroRelease()
                    return
                else:
                    #Else send the request to the front-end user
                    return self.connected_server.user_requests(data)			
            #Catch connection errors to front-end server; try to reconnect at 5 second intervals
            except Pyro4.errors.ConnectionClosedError:
                print("Cannot establish connection to front-end server; trying again in 5 seconds...")
                sleep(5)
                try:
                    ns = Pyro4.locateNS()
                    self.server = ns.lookup("JH-front-end")
                    self.connected_server = Pyro4.Proxy(self.server)
                    i += 1
                except Pyro4.errors.CommunicationError:
                    print("Could not establish connection. Exiting program")
                    sys.exit()
            except Pyro4.errors.CommunicationError:
                print("Cannot establish connection to front-end server; trying again in 5 seconds...")
                sleep(5)
                ns = Pyro4.locateNS()
                self.server = ns.lookup("JH-front-end")
                self.connected_server = Pyro4.Proxy(self.server)
                i += 1   
        #If all 5 connection attempts failed, exit the user interface
        print("No connection could be established.")
        sys.exit()

#Render the possible user commands on screen 
def display_ui():
    print("\nWelcome to the Just Hungry food delivery service!\n")
    print("     1  -   Create a New Order")
    print("     2  -   Retrieve Your Order History")
    print("     3  -   Cancel an Existing Order")
    print("     4  -   Quit\n")
    return

#Parse user input and call appropriate function depending on the number provided
def manage_user_input(user):	
    while True :
        display_ui()	
        user_selection = input("To proceed, select an option from the list above: ")
        valid_input_options = ["1", "2", "3", "4"]
        #Catch invalid input 
        while user_selection == '' or user_selection not in valid_input_options:
            user_selection = input("\nInvalid option selected. Please try again: ")
        if user_selection == '1' :
            user.create_new_order()
        elif user_selection == '2' :
            user.view_orders()
        elif user_selection == '3' :
            user.cancel_order()
        elif user_selection == '4' :
            #Quit
            user.quit()
            return

#Initialize a new instance of the User object
def main() :
    user = User()
    manage_user_input(user)

#Call main function on program start	
if __name__ == "__main__" :
    main()