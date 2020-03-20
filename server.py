from __future__ import print_function
import Pyro4
import sys
import requests 

@Pyro4.expose
@Pyro4.behavior(instance_mode="single")

#Intialize back-end server object 
class JustHungry(object):
    def __init__(self, number, daemon):
        #Manage customer orders via dictionary; keys represent unique customer IDs
        self.active_orders = {}
        #Maintain a queue of other existing back-end servers
        self.servers = []
        self.daemon=daemon
        self.is_primary = False
        self.server_status="Available"
        #When reassigning the primary, check whether replica has just been initialized; if yes, this indicates outdated backup
        #Just_initialized = 1 indicates that the replica has been propagated most recent data and can thus be selected as a valid primary 
        self.just_initialized = 0
        #Intialize a sample product inventory
        self.product_inventory = [["apple", 15, 1.99],["banana", 20, 0.55],["orange", 15, 0.79],["bread", 4, 2.25],["flour", 0, 4.55], ["tomato", 17, 0.65], ["kale", 6, 0.99]]
    
    #Update server orders and product inventory
    def current_order_status(self, status):
       self.active_orders = status
       print("\nCurrent active orders: ", self.active_orders)
    def current_inventory_status(self, status):
       self.product_inventory = status
       print("\nCurrent product inventory: ", self.product_inventory)
    
    #Return the current status of the server ("Available" or "Offline")
    def current_server_status(self):
        return self.server_status

    #Set the current server to primary 
    def make_primary(self):
        self.is_primary = True
        self.just_initialized = 1
        return
    
    #Check if the current server has primary status
    def check_primary(self):
        if self.is_primary == True:
            return True
        else:
            return False
    
    #Check if the current server has just been initialized or contains most recently propagated data 
    def check_init(self):
        #Server has just been initalized or rebooted; outdated backup and thus not a valid choice for new primary
        if self.just_initialized == 0:
            return 0
        #Replica has most recently propagated backup; valid as a potential new primary
        else:
            return 1

    #Propagate state of primary server to remaining servers in queue
    def propagate_backup(self):
        if self.is_primary == False:
            return False
        else:
            print("\nCurrent primary - propagating to replicas")
            for server in self.servers:
                if server.check_primary() == False:
                    try:
                        ack = server.update_status(self.active_orders, self.product_inventory)
                        #Wait for acknowledgement that copy of primary was propagated to replica
                        if ack == True:
                            print("Updated status of replica server: ", server)
                        else:
                            print("Failed to update status of replica server: ", server)
                    except:
                        print("Failed to update status of replica - server offline.")
                else:
                    print("As the current primary server, not propagating to self")
                    self.just_initialized = 1
        return True
    
    #Update the status of a replica server to match the state of the current primary
    def update_status(self,orders,inventory):
        try:
            print("\nReceived updates from primary server - updating replica.")
            self.active_orders = orders
            print("\nActive orders: ")
            print(self.active_orders)
            self.product_inventory = inventory
            print("\nProduct inventory: ")
            print(self.product_inventory)
            self.just_initialized = 1
            return True
        except:
            print("\nFailed to update status of replica server.")
            return False

    #Clear the server queue
    def clear_servers(self):
	    self.servers = []

    #Update most current server queue of active connections
    def init_server_queue(self, servers):
        for server in servers:
            self.servers.append(Pyro4.Proxy(server))
    
    #JustHungry order functionalities

    #Create a new user
    def new_user(self, user_id, user_inp):
        #Validate supplied user zip code using external API service (postcodes.io)
        def verify_postcode(zip):
            parsed_zip = zip.replace(" ", "%20")
            print("\nCalled API to validate zipcode", zip)
            URL = 'https://api.postcodes.io/postcodes/'+parsed_zip+'/validate/'
            try:
                r = requests.get(URL)
                res = r.json()
                validation = (res['result'])
                #Validation call returns True/False for valid/invalid zip code
                return validation 
            #If API call failed, catch the error and return to user
            except:
                print("Failed to perform validation of postal code via external API call.")
                resp = "Failed to perform validation of postal code via external API call."
                return resp
    
        supplied_zip = user_inp[3]
        #Verify the supplied zip code
        zip_status = verify_postcode(supplied_zip)
        if zip_status == False:
            resp = "Invalid delivery zip code."
            return resp
        #If the zip code is valid, proceed to initialize a new user 
        elif zip_status == True:
            print("\nInitializing a new user in active orders...\n")
            #Check if this user has registered before; if not, create a new key at the unique user ID
            if user_id not in self.active_orders:
                self.active_orders[user_id] = []
                self.active_orders[user_id].append(user_inp)
            #Otherwise, if this is a recurring user, update user contact details as needed
            else:
                self.active_orders[user_id][0] = user_inp
            resp = "Customer details verified."
            #Propagate new server state to other back-end replicas
            self.propagate_backup()
            return resp
        #If invalid zip code, do not create a new user; return error to user and wait for new zip code before proceeding
        elif zip_status == "Failed to perform validation of postal code via external API call.":
            return zip_status
        else: 
            resp = "Zip code validation failed, please try again later."
            return resp 

    #Retrieve the current product list in and inventory stock
    def current_product_list(self):
        try:
            #If no products in the inventory, return error to user
            if len(self.product_inventory) == 0:
                return "Product list is empty, please try again later."
            #Otherwise return the array of products and their stock/prices 
            else:
                return self.product_inventory
        except:
            return "Could not retrieve product list, please try again later."
    
    #Calculate the total cost a of a user's order
    def total_order_cost(self,user_id,user_inp):
        proposed_order = user_inp
        total_cost = 0
        for entry in proposed_order:
            for item in self.product_inventory:
                if entry[0] == item[0]:
                    total_cost += (entry[1]*item[2])
        return total_cost

    #Create a new order at a specified user ID
    def new_order(self,user_id,user_inp):       
        try:
            requested_products = user_inp[1]
            #Check if there is sufficient stock of each requested item
            for entry in requested_products:
                for item in self.product_inventory:
                    #If there is insufficient stock, return an error message with the problematic item
                    if entry[0] == item[0]:
                        if entry[1] > item[1]:
                            return "Could not place order due to low stock of " + entry[0]+". Please try again later."
                        else:
                            #Update the stock count
                            item[1] -= entry[1]
            self.active_orders[user_id].append(user_inp)
            #Propagate changes to other backend replicas
            self.propagate_backup()
            #Return that the order has been placed successfully
            return "Order placed succesfully. Please pay on delivery."
        #Catch any error encountered during placing the order and return 
        except:
            return "Could not place order. Please try again later."

    #Retrieve the order history for a particular user
    def order_history(self, user_id):
        try:
            return self.active_orders[user_id]
        except:
            return "Could not retrieve any orders for this user."
    
    #Retrieve a list of active orders for a particular user
    def view_active_orders(self, user_id):
        all_orders = self.active_orders[user_id]
        try:
            all_orders = self.active_orders[user_id]
            active = []
            i = 0
            for order in all_orders:
                if i != 0:
                    if order[2] == 'Active':
                        active.append(order)
                i += 1
            #If no active orders found
            if len(active) == 0:
                return "No active orders for this user."
            #Else return the list of active orders
            return active
        except:
            return "Could not retrieve active orders for this user."

    #Delete an order at specified user ID and order ID
    def delete_order(self, user_id, user_inp):
        try:
            order_id = user_inp
            #Update status of order to 'Cancelled' at particular user_id and order_id 
            i = 0
            for entry in self.active_orders[user_id]:
                if i != 0:
                    if entry[0] == int(order_id):
                        entry[2] = "Cancelled"
                i += 1
            #Propagate server updates to other backend replicas
            self.propagate_backup()
            return "Successfully deleted order " + str(order_id)+ "."
        except:
            return "Error deleting order."



def main(server_number):
    #Initialize the back-end server object and register in Pyro name server
	try:
		daemon = Pyro4.Daemon()
		ns = Pyro4.locateNS()
		m = JustHungry(str(server_number),daemon)
		uri = daemon.register(m)
		ns.register("backend.JH_orders_" + str(server_number), uri, metadata={"backend"})
		print("Back-end URIs: " , "JH_orders_" + str(server_number), uri)
		daemon.requestLoop()
		daemon.close()
		print("Daemon closed")
    #If the name server has not been initialized yet, throw an error
	except Pyro4.errors.NamingError:
		print("Could not find the name server; please start the server by typing 'pyro4-ns' in the command prompt.")


#Initialize back-end server; supplied sys.argv is appended to the server name
if __name__ == "__main__":
	server_number = sys.argv[1]
	main(server_number)