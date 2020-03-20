import Pyro4
from Pyro4.errors import CommunicationError, PyroError, ConnectionClosedError
from time import sleep
import sys


@Pyro4.expose
#Front-end server object
class FrontEnd(object):
    def __init__(self,daemon):
        #Initialize PYRO daemon and locate name server
        self.daemon = daemon
        self.ns = Pyro4.locateNS()
        #Dynamically retrieve list of active backend servers 
        self.connected_servers = self.locate_replica()
        #Upon establishing initial connection, assign primary by picking back-end server at front of queue; all replicas are identical at this point - thus update precendence is not a concern
        self.current_server = Pyro4.Proxy(self.connected_servers[0][1])
        self.current_primary = self.connected_servers[0]
        self.current_server.make_primary()
        print("Initialized front-end connection.\n")
        return 
    
    #Terminate front-end server connection
    @Pyro4.oneway
    def shutdown(self):
        print("Shutting down front-end server...")
        self.daemon.shutdown()
        sys.exit(1)
    
    #Retrieve a list of active replicas
    def locate_replica(self):
        try:
            self.server_uris = self.ns.list(metadata_all={"backend"}) 
            connected_uris = []
            raw_uris = []
            print("\n")
            #Iterate through list of back-end replicas and retrieve their current status
            for (server, uri) in self.server_uris.items():
                try:
                    with Pyro4.Proxy(uri) as replica:
                        current_status = replica.current_server_status()
                        print("The current status of " + server + " is " + current_status)
                        #If the replica status is not offline, append it to the list of active backend connections 
                        if current_status != "Offline":
                            connected_uris.append((server, uri)) 
                            raw_uris.append(uri)
                #Catch server disconnects that were previously in list of active connections
                except CommunicationError:
                    print("The server " + server + " is currently offline.")
            print("\n")
            #Check that sufficient back-end servers are active
            if len(connected_uris) < 2:
                raise Pyro4.errors.CommunicationError
            if len(connected_uris) >= 2:
                #Propagate list of active servers across all connected backends
                for uri in connected_uris:
                    Pyro4.Proxy(uri[1]).clear_servers()
                    Pyro4.Proxy(uri[1]).init_server_queue(raw_uris)
                return connected_uris
        #Throw an error if the name server cannot be found 
        except Pyro4.errors.NamingError:
            print ("Name server cannot located back-end servers; please start it first and then initialize the front-end server")
            self.shutdown()
            #return
        #Throw an error if insufficient back-end servers active; at least 2 required
        except Pyro4.errors.CommunicationError:
            print("Cannot locate sufficient active back-end servers; at least one 1 primary and 1 replica server are necessary to maintain integrity of resources.")
            self.shutdown()
            return
  
    def user_requests(self, request_body):
        #Upon receiving a new request, update list of available replicas
        self.connected_servers = self.locate_replica()
        #Check if existing primary is still in list of active servers; if not, assign a new primary
        if self.current_primary not in self.connected_servers:
            print("Delegating a new primary server - the previous primary is no longer active")
            #Delegate new primary by comparing server initialization status; iterate through active backend servers and assign one with self.just_initialized = 1 as the new primary
            assigned_new_primary = 0
            for candidate in self.connected_servers:
                if Pyro4.Proxy(candidate[1]).check_init() == 1:
                    self.current_server = Pyro4.Proxy(candidate[1])
                    self.current_primary = candidate
                    self.current_server.make_primary()
                    assigned_new_primary = 1
                    print("Found a new primary")
                    break
            if assigned_new_primary == 0:
                print("Could not locate an up to date replica to be the new primary; choosing next most up to date server from front of server queue")
                self.current_server = Pyro4.Proxy(self.connected_servers[0][1])
                self.current_primary = self.connected_servers[0]
                self.current_server.make_primary()
        #Once a primary is established, execute the received request 
        request = request_body['request']
        user_id = request_body['user_id']
        user_inp = request_body['user_inp']

        #User requests are sorted by type and forwarded to backend
        if request == "USER_DETAILS":
            print("Updating user details for user ", user_id)
            response = self.current_server.new_user(user_id, user_inp)
            print("Server response: ", response)
            return str(response)
        
        if request == "PRODUCT_LIST":
            print("Retrieving current product list and inventory")
            response = self.current_server.current_product_list()
            print("Server response: ", response)
            return response
        
        if request == "ORDER_COST":
            print("Calculating total cost of order for user ", user_id)
            response = self.current_server.total_order_cost(user_id, user_inp)
            print("Server response: ", response)
            return response

        elif request == "PLACE_ORDER":
            print("Placing an order for user ", user_id)
            response = self.current_server.new_order(user_id, user_inp)
            print("Server response: ", response)
            return response
        
        elif request == "VIEW_ORDERS":
            print("Retrieving order history for user ", user_id)
            response = self.current_server.order_history(user_id)
            print("Server response: ", response)
            return response
        
        elif request == "VIEW_ACTIVE":
            print("Retrieving a list of active orders for user ", user_id)
            response = self.current_server.view_active_orders(user_id)
            print("Server response: ", response)
            return response

        elif request == "CANCEL":
            print("Cancelling an order for user ", user_id)
            response = self.current_server.delete_order(user_id, user_inp)
            print("Server response: ", response)
            return response

        #Catch invalid request types from user
        else:
            return "Request type " + request + " not supported."

def main():
    connection_attempt = 1
    while connection_attempt !=6:
        try:
            #Initialize front-end connection to Pyro name server
            daemon = Pyro4.Daemon()
            ns = Pyro4.locateNS()
            front_end = FrontEnd(daemon)
            uri = daemon.register(front_end)
            ns.register("JH-front-end", uri)
            print("Front-end URI: ",uri)
            daemon.requestLoop()
            daemon.close()
            break
        #If back-end connection lost or cannot be established, attempt to re-connect 5 times in 10 second intervals
        except Pyro4.errors.CommunicationError:
            print("Connection attempt:", connection_attempt)
            print("Servers are not found; trying again in 10 seconds.")
            sleep(10)
            connection_attempt += 1 
        except Pyro4.errors.NamingError:
            print("Connection attempt:", connection_attempt)
            print("Name server not found; start by typing 'pyro4-ns' in the command prompt. Trying again in 10 seconds.")
            sleep(10)
            connection_attempt += 1 

    #Else break out of connection attempt loop and close front-end server, terminating all connected users 
    if connection_attempt == 5:
        print("Reached maximum of 5 connection attempts to front-end server; try again later. Quitting.")
        sys.exit()

if __name__ == "__main__":
	main()