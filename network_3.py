import queue
import threading
import json
import copy


## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)
    
    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)
            
        
## Implements a network layer packet.
class NetworkPacket:
    ## packet encoding lengths 
    dst_S_length = 5
    prot_S_length = 1
    
    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S
        
    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()
        
    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise('%s: unknown prot_S option: %s' %(self, self.prot_S))
        byte_S += self.data_S
        return byte_S
    
    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0 : NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length : NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise('%s: unknown prot_S field: %s' %(self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length : ]        
        return self(dst, prot_S, data_S)
    

    

## Implements a network host for receiving and transmitting data
class Host:
    
    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False #for thread termination
    
    ## called when printing the object
    def __str__(self):
        return self.addr
       
    ## create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out') #send packets always enqueued successfully
        
    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))
       
    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return
        


## Implements a multi-interface router
class Router:
    
    ##@param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        #save neighbors and interfeces on which we connect to them
        self.cost_D = cost_D    # {neighbor: {interface: cost}}
        self.rt_tbl_D = {}      # {destination: {router: cost}}
        for neighbor in self.cost_D:
            for interface, cost in self.cost_D[neighbor].items():
                self.rt_tbl_D[neighbor] = { self.name: cost }
                break
        self.rt_tbl_D[self.name] = { self.name: 0 }
        print('%s: Initialized routing table' % self)
        self.print_routes()
    
        
    ## Print routing table
    def print_routes(self):
        print(self.rt_tbl_D)
        bars = "======"
        dividers = "------"
        header = "| " + self.name + " | "
        routers = {}
        empty_tile = " ~ | "
        columns = 0
        the_whole_table = ''
        for entry in self.rt_tbl_D:
            bars += "====="
            dividers += "-----"
            header += entry + " | "
            for router in self.rt_tbl_D[entry]:
                if router not in routers:
                    routers[router] = "| " + router + " | "
                    for i in range(columns):
                        routers[router] += empty_tile
                routers[router] += " " + str(self.rt_tbl_D[entry].get(router)) + " | "
            columns += 1
        the_whole_table += bars + '\n'
        the_whole_table += header + '\n'
        the_whole_table += bars + '\n'
        num_routers = 0
        for router in routers:
            the_whole_table += routers[router] + '\n'
            if num_routers < len(routers) - 1:
                the_whole_table += dividers + '\n'
            num_routers += 1
        the_whole_table += bars + '\n'
        print(the_whole_table)


    ## called when printing the object
    def __str__(self):
        return self.name


    ## look through the content of incoming interfaces and 
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            #get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            #if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p,i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))
            

    ## forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            chosen_neighbor = ''
            if p.dst in self.cost_D:
                chosen_neighbor = p.dst
            else:
                best_cost = 100
                best_router = ''
                for router in self.rt_tbl_D[p.dst]:
                    if router != self.name and router in self.cost_D and self.rt_tbl_D[p.dst][router] < best_cost:
                        best_cost = self.rt_tbl_D[p.dst][router]
                        best_router = router
                chosen_neighbor = best_router
            chosen_interface = 42
            for k, _ in self.cost_D[chosen_neighbor].items():
                chosen_interface = k
                break
            if chosen_interface == 42:
                print('%s: somehow, there are no interfaces available, dropping packet %s' %(self, p))
            else:
                self.intf_L[chosen_interface].put(p.to_byte_S(), 'out', True)
                print('%s: forwarding packet "%s" from interface %d to %d' % \
                    (self, p, i, chosen_interface))
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        p = NetworkPacket(0, 'control', json.dumps(self.rt_tbl_D))
        try:
            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## Send route update to all neighboring routers
    def notify_neighbors(self):
        for neighbor in self.cost_D:
            if neighbor[0] == 'R':
                for k, _ in self.cost_D[neighbor].items():
                    self.send_routes(k)
                    break


    ## forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        print('%s: Received routing update "%s" from interface %d' % (self, p, i))
        rcv_tbl_D = json.loads(p.data_S) # decode the routing update into a dictionary
        old_tbl_D = copy.deepcopy(self.rt_tbl_D) # copy original routing table for later comparison
        routers = [] # Keep a list of routers for later table update

        for neighbor in rcv_tbl_D:
            # Create an entry for a new neighbor
            if neighbor not in self.rt_tbl_D:
                self.rt_tbl_D[neighbor] = {}
            best_cost = 100 # high starting cost for comparison
            best_router = ''
            for router in rcv_tbl_D[neighbor]:
                if router not in routers:
                    routers.append(router)
                # If there's already an entry for this router, compare costs
                if self.rt_tbl_D[neighbor].get(router) is not None:
                    if rcv_tbl_D[neighbor][router] < self.rt_tbl_D[neighbor][router]:
                        self.rt_tbl_D[neighbor][router] = rcv_tbl_D[neighbor][router]
                else:
                    self.rt_tbl_D[neighbor][router] = rcv_tbl_D[neighbor][router]
                    # If the neighbor isn't self and it's not directly connected to self, find the lowest cost to it
                    if neighbor != self.name and neighbor not in self.cost_D:
                        if router in self.cost_D and rcv_tbl_D[neighbor][router] < best_cost:
                            best_cost = rcv_tbl_D[neighbor][router]
                            best_router = router
            if best_router != '':
                self.rt_tbl_D[neighbor][self.name] = self.rt_tbl_D[best_router][self.name] + best_cost

        # Handle implicit update of neighbors not represented in the update packet data
        for neighbor in self.rt_tbl_D:
            if neighbor not in rcv_tbl_D:
                for router in routers:
                    self.rt_tbl_D[neighbor][router] = self.rt_tbl_D[router][self.name] + self.rt_tbl_D[neighbor][self.name]

        # If the routing table has changed at all, notify neighbors of the update
        if self.rt_tbl_D != old_tbl_D:
            self.notify_neighbors()
        else:
            for neighbor in self.rt_tbl_D:
                if self.rt_tbl_D[neighbor] != old_tbl_D[neighbor]:
                    self.notify_neighbors()
                    break
                else:
                    break_out = False
                    for r, c in self.rt_tbl_D[neighbor].items():
                        if old_tbl_D[neighbor][r] != c:
                            self.notify_neighbors()
                            break_out = True
                            break
                    if break_out:
                        break

        self.print_routes()

                
    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return 
