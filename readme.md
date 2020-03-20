
# Distributed Systems Summative Assignment - Just Hungry

## Source Code Documentation

### Running the System

1. Navigate to the directory containing files server.py, client.py, user.py. 
2. Initialize the Pyro name server by typing 'pyro4-ns' in the command prompt.
3. Initialize back-end servers by typing 'python server.py 1', 'python server.py 2', 'python server.py 3', etc. in the command prompt. The system can support an unlimited number of back-end servers under any naming scheme; the value of the supplied command line argument will be used to identify the server in the Pyro name server. If there are multiple versions of Python installed on the current machine, specify Python 3 by calling 'python3 server.py server#'. 
4. Initialize the front-end server by typing 'python client.py' in the command prompt. 
5. Initialize a Just Hungry user by typing 'python user.py' in the command prompt. The system can support multiple simultaneous users at any one time; requests are handled in order recevied by the front-end server. 

To mimic a real-time distributed system, shutdown servers by pressing 'control-C' in the respective terminal window. Likewise, re-engage offline servers by calling the respective command in the terminal window.

A passive replication scheme is implemented to ensure that the user experience is not compromised in the event of a back-end server outage (discussed further below). Reassignment of the primary back-end server is handled by the front-end server in client.py, and user requests are handled without interupption if the current primary back-end server goes offline. To fulfill transparency requirements of a distributed system, the user is under the impression that they are interacting with a single server (client.py); the distributed nature of system components across multiple back-end servers is not apparent to the user.

### External Web Services

The system makes use of 3rd party API 'postcodes.io' to validate user postal codes. Users are prompted to supply a postal code, among other contact details, when creating a new order. If the postal code is valid (the API call returns a boolean 'True'), the user is prompted with an order screen containing current product inventory, stock, and pricing. If the postal code is invalid (API call returns a boolean 'False'), user is prompted to provide a new postal code which is subsequently sent for validation; a user will not be able to view products, add items to their cart, and place an order until their postal code has been successfully validated.

Exception handling has been added for robustness; the system manages failed API calls by returning an error message and reinitiating the request on valid user input. 


### System Design Diagram

See attached **JHsystem_design_diagram.pdf** for illustration of system workflows and interactions between the back-end servers, front-end servers, and user interface. 

____________________________________________________________

### System Functionality and Error Handling

The system implements a passive replication scheme to maintain data integrity and fulfill the location, relocation, replication, and failure transparency requirements of a distributed system.

Upon initialization of the front-end server (client.py), a queue of available back-end servers is generated; as no user requests have yet been handled by the front-end server, all back-end server data is identical and in its initial state. Thus the primary server is assigned as the back-end server at the front of the queue. 

At each subsequent request, the front-end server call to locate_replicas() returns an updated list of available back-end servers. If the current primary server URI is not in this list, one of the available replicas is promoted as the new primary; otherwise the primary server remains unchanged.

To maintain data integrity and avoid data loss between requests, it is critical that an up-to-date replica is chosen as the new primary. The parameter value self.is_initialized is used to keep track of a replica's update status; the parameter value is set to 1 when a replica recevies a copy of backup data from the primary. Thus, the new primary is always chosen as a replica with self.is_initialized = 1, indicating that it has received data from the most recently executed request. In the event that such a replica is not available, the replica at the front of the connected servers queue is promoted.

At any one time, a primary server and at least one active replica are required to maintain integrity of the system data. If less than 2 available back-end servers are detected before executing a request, the front-end server returns an error message to the user and shutsdown. 

#### User.py

The user interface enables users to fulfill 3 primary functionalities: create new orders, view existing orders, and cancel orders. Users are also granted the option to exit the system and disconnect from the the front-end server.


1. Creating New Orders

- If the user has not already placed a Just Hungry order during this session, they are prompted to enter contact details, including:
    - First name
    - Last name
    - Phone number
    - Postal code
    - Addresss
- User input is validated to ensure that it is non-empty, and that the supplied phone number is numeric/hyphenated. Each user is also assigned a unique user ID, which is utilized by the server to associate orders with users. 
- User contact details are then sent to and stored on the server; the server attempts to validate the user's postal code. If the postal code is invalid, the user is prompted to re-enter input until a valid postal code is obtained.
- If this is not the user's first Just Hungry order, they are presented with their current contact details; they are asked to confirm that the information presented is correct, otherwise they are prompted to update it. 

- The user is presented with an up-to-date list of available products, as well as their current stock and price. 
    - The user can add products to their cart, specifying a quantity for each product.
    - Once the user indicates that they would like to place their order, they are prompted to review their final cart and confirm that they intend to proceed. Here, the user can view the total cost of their order. 

- The user is presented with 3 delivery options. The shipping cost of the selected option is added to the total cost of their order.

- The user is presented with the option to add a tip. If the user agrees to add a tip, the tipped amount is added to the total cost of their order.

- The order contents are sent to the server; a confirmation message is displayed indicating if the order was placed succesfully or not.


2. Viewing Order History

- A user can view a list of all of their past orders sorted by order ID; metrics include order status (Active/Cancelled), chosen delivery method, products/quantities purchased, and total order cost.


3. Cancelling an Order

- A user is presented with a list of all of their active orders. They are prompted to input the order ID of the order they would like to cancel, upon which the order status is updated to 'Cancelled'.

The function create_request() is used to relay user input and associated request type to the front-end server. 

If connection to the front-end server is interrupted, an exception is raised and user.py attempts to reconnect at 5 second intervals; if a connection is not re-established after 5 attempts, an error message is displayed and the program exits. 

#### Client.py

The front-end server serves as an intermediary between the user interface and back-end servers; user requests are piped through the front-end server to the back-end servers. The front-end server identifies the request type initiated by the user, and calls the appropriate function(s) from back-end system components. 

**Request types include:**

- Requests to update: after each update request, the primary server propagates a backup of its current state to all active replicas

    - USER_DETAILS: update or append user details at particular user ID

    - PLACE_ORDER: create a new order at a particular user ID

    - CANCEL: cancel an order (identified by order ID) for a particular user ID

- Requests to retrieve existing content:    
    - PRODUCT_LIST: retrieve current product list and inventory

    - ORDER_COST: calculate and return the total cost of a user's order

    - VIEW_ORDERS: retrieve order history for a specific user ID

    - VIEW_ACTIVE: retrieve a list of active orders for a specific user ID

The front-end server also manages reassigning of the primary server, keeping track of all connected back-end servers and ensuring that a replica with the most recent copy of data is promoted.  

Exception handling for server connection status has been added for robustness. If the front-end server cannot locate the name server, a NamingError is thrown and the program terminated. Likewise, if the front-end server locates insufficient back-end servers to connect to (less than 2), a ConnectionError is thrown and the program is terminated. 

#### Server.py

Server.py fulfills requests received from client.py, facilitating  functionality of and acting as a centralized data point for the overarching Just Hungry system; each request type indicated in client.py has a corresponding function which is called in server.py:

- new_user(); append a new user to active_users
- current_product_list(); retrieve the current state of the product inventory
- total_order_cost(); compute the total cost a user's order
- new_order(); initiate a new order in active_orders for a specific user_id
- order_history(); retrieve the order history for a specific user_id
- view_active_orders(); retrieve active orders for a specific user_id
- delete_order(); change the status of specified order id to 'Cancelled' for a specific user_id

Server.py also includes a series of status management functions, such as make_primary(), check_primary(), update_status(), clear_servers(), and init_server_queue(). These functions are used to establish the current state and status (Active/Offline) of each back-end server in relation to other back-end servers; depending on the status of each server, an appropriate primary is selected by the front-end server. In particular, clear_servers() and init_server_queue() provide a global view of available back-end servers in the distributed system, clearing and initializing an updated list of connected replicas, respectively. 

Server responses are collected by the front-end server client.py, and subsequently relayed back to the user interface in user.py. In the event that a back-end server encounters an error when fulfilling a request, a exception is raised and appropriate error message is returned.

Requests which involve updating server state (i.e. making changes to data stored in the active_orders and product_inventory arrays) are followed by a call to propagate_backup(), whereby the primary server distributes a copy of its current data to all active replicas. Data is propagated from the primary to replicas on each update request, ensuring that all replicas are up-to-date with the most recent data on each incoming request.

