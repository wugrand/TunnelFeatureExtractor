# import PacketAnalyzer
# import PacketDigester

from scapy.all import *
from collections import Counter, namedtuple
import math
import zlib as zl
import binascii as b2a

class PcapFeatures(object):

    def __init__(self, file_path, protoLabel):
        '''

        :param file_path: Set file path with 'None' if file_path given (indicates that it's a filtered pcap)
                else. set the actual file_Path
        :param protoLabel: Used to label the base file where the pcap file-path will be stored
        :return:
        '''

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        #self.logger.setLevel(logging.INFO)
        self.logger.setLevel(logging.DEBUG)
        #self.logger.setLevel(logging.WARNING)

        self.pcapFilePath = str(file_path).strip()
        self.pcapFileName = ''
        try:
            if len(file_path) > 0:
                # self.pktReader = PcapReader(self.pcapFilePath)
                # Note the difference between the ABOVE and with '.read_all' BELOW
                self.pktReader = PcapReader(self.pcapFilePath).read_all()
                # CHECK THE LINE ABOVE IF MEMORY ISSUES ARISE FOR LARGE PCAP FILES
                self.pcapFileName = str(self.pcapFilePath).rsplit('/',1)[1]
                self.logger.debug("Pcap File Name: %s" % self.pcapFileName)
        except:
            self.logger.warning("Pcap File MISSING at : [%s] or Filtered PCAP" % self.pcapFilePath)

        self.protocolLabel = protoLabel

        self.pktCharFreqDict = {}
        self.pktCharEntropySeq = []
        self.specificPktLens = []

        #self.fig, self.ax = plt.subplots()
        #Originally plots were initialized here when the object was created
        #For memory reasons figures/plots/axes are initialized now only just before plotting
        self.fig = None #plt.figure()
        self.ax = None #plt.axes()

        self.logger.info("Finished initializing and reading pcap file ...")
        self.logger.debug("Type : %s" % str(type(self.pktReader)))

    def test_pkt_Reader(self):
        self.logger.debug("Type : %s" % str(type(self.pktReader)))
        #pktlen_seq = [len(pkt[IP]) for pkt in self.pktReader if UDP in pkt]
        pktlen_seq = [len(pkt[IP]) for pkt in self.pktReader if UDP in pkt]
        self.logger.debug("Length of Seq: %i" % len(pktlen_seq))

        return pktlen_seq

    def add_proto_label(self, newProtoLabel):
        self.protocolLabel = newProtoLabel

    def get_proto_label(self):
        return self.protocolLabel

    def calcEntropy(self, myFreqDict):
        '''
        Entropy calculation function
        H(x) = sum [p(x)*log(1/p)] for i occurrences of x
        Arguments: Takes a dictionary containing byte/char keys and their frequency as the value
        '''
        h = 0.0
        for aKey in myFreqDict:
            # Calculate probability of each even occurrence
            prob = myFreqDict[aKey]/sum(myFreqDict.values())
            # Entropy formula
            h += prob * math.log((1/prob),2)
        return h

#-----------------------------------#
###### DNS Related Methods ##########
#-----------------------------------#
    def get_ip_pkt_dns_req_entropy(self):
        '''
        :return:
        '''
        self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(pkt[IP])))
                                  for pkt in self.pktReader if UDP in pkt and pkt[UDP].dport == 53]
        return self.pktCharEntropySeq

    def getDnsPktEntropy(self):
        '''
        :return:
        '''
        self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(pkt[IP][UDP][DNS])))
                                  for pkt in self.pktReader if UDP in pkt and pkt[UDP].dport == 53]
        return self.pktCharEntropySeq

    def getDnsReqLens(self):
        self.specificPktLens = [len(pkt[IP][UDP][DNS])
                                for pkt in self.pktReader if UDP in pkt and pkt[UDP].dport == 53]
        return self.specificPktLens

    def getDnsReqQnames_upstream(self):
        ### self.dnsQnames = [pkt[DNSQR].qname
        ###                   for pkt in self.pktReader if pkt.haslayer(DNS) and pkt[UDP].dport == 53]
        # From the documentation /reverse engineering Iodine (IP-Over-DNS) by Stalkr it is seen that:
        #  - Client (upstream) REQUESTS are encoded, compressed and placed into the 'DNS Query Name', while
        #  - Server (downstream) RESPONSES are only optionally compressed and placed into the 'DNS Resource Record'.
        self.dnsReqQnames = []
        topdomain = b'.barns.crabdance.com.'
        for pkt in self.pktReader:
            # if UDP in pkt and DNSQR in pkt and len([DNSQR].qname) > 0 and pkt[UDP].dport==53:
            if pkt.haslayer(DNS) and pkt[UDP].dport==53:
                # scapy_qry_req = pkt[IP][UDP][DNS][DNSQR].qname
                scapy_qry_req = pkt[DNSQR].qname
                if topdomain in scapy_qry_req:  # To filter out any other random DNS requests that might exist in pcap
                    scapy_cleaned_qry_req = scapy_qry_req[5:-len(topdomain)].replace(b'.', b'')
                    #scapy_cleaned_decompressed_qry_req = zl.decompress(scapy_cleaned_qry_req)
                    #self.dnsReqQnames.append(scapy_cleaned_qry_req) # <<---- Puts byte arrays into list (but has issues with JSON later)

                    # Convert the python3 byte array to regular strings (latin-1)   # <---- Seems to work with JSON but results in long unicode strings
                    # scapy_cleaned_qry_req_str = scapy_cleaned_qry_req.decode('latin-1')  # decode('utf-8')
                    # self.dnsReqQnames.append(scapy_cleaned_qry_req_str)

                    #convert the python3 byte array to hex strings (every pair of digits is a byte / individual hex value)
                    scapy_cleaned_qry_req_hexstr = b2a.hexlify(scapy_cleaned_qry_req).decode()
                    self.dnsReqQnames.append(scapy_cleaned_qry_req_hexstr)

        return self.dnsReqQnames

    def getDnsReqQnameEntropy_upstream(self):
        # From the documentation /reverse engineering Iodine (IP-Over-DNS) by Stalkr it is seen that:
        #  - Client (upstream) REQUESTS are encoded, compressed and placed into the 'DNS Query Name', while
        #  - Server (downstream) RESPONSES are only optionally compressed and placed into the 'DNS Resource Record'.

        topdomain = b'.barns.crabdance.com.'
        for pkt in self.pktReader:
            # if UDP in pkt and DNSQR in pkt and len([DNSQR].qname) > 0 and pkt[UDP].dport==53:
            if pkt.haslayer(DNS) and pkt[UDP].dport==53:
                # scapy_qry_req = pkt[IP][UDP][DNS][DNSQR].qname
                scapy_qry_req = pkt[DNSQR].qname
                if topdomain in scapy_qry_req:  # To filter out any other random DNS requests that might exist in pcap
                    scapy_cleaned_qry_req = scapy_qry_req[5:-len(topdomain)].replace(b'.', b'') # Picks from 5th character upto just before "topdomain"
                    #scapy_cleaned_decompressed_qry_req = zl.decompress(scapy_cleaned_qry_req)

                    self.pktCharEntropySeq.append(self.calcEntropy(Counter(bytes(scapy_cleaned_qry_req))))

        # self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(scapy_qry_req)))
        #                           for pkt in self.cap if UDP in pkt and DNSQR in pkt
        #                           and len([DNSQR].qname) > 0 and pkt[UDP].dport==53]
        return self.pktCharEntropySeq

    def getDnsReqQnameEntropy_upstream_x_bytes(self, x_bytes_len):
        # From the documentation /reverse engineering Iodine (IP-Over-DNS) by Stalkr it is seen that:
        #  - Client (upstream) REQUESTS are encoded, compressed and placed into the 'DNS Query Name', while
        #  - Server (downstream) RESPONSES are only optionally compressed and placed into the 'DNS Resource Record'.
        pktCharEntropySeq_x_bytes = []
        topdomain = b'.barns.crabdance.com.'
        for pkt in self.pktReader:
            # if UDP in pkt and DNSQR in pkt and len([DNSQR].qname) > 0 and pkt[UDP].dport==53:
            if pkt.haslayer(DNS) and pkt[UDP].dport==53:
                # scapy_qry_req = pkt[IP][UDP][DNS][DNSQR].qname
                scapy_qry_req = pkt[DNSQR].qname
                if topdomain in scapy_qry_req:  # To filter out any other random DNS requests that might exist in pcap
                    scapy_cleaned_qry_req = scapy_qry_req[5:-len(topdomain)].replace(b'.', b'') # Picks from 5th character upto just before "topdomain"
                    #scapy_cleaned_decompressed_qry_req = zl.decompress(scapy_cleaned_qry_req)
                    # trunc_qry_req = ''
                    if x_bytes_len > len(scapy_cleaned_qry_req):
                        trunc_qry_req = scapy_cleaned_qry_req[:len(scapy_cleaned_qry_req)]
                    else:
                        trunc_qry_req = scapy_cleaned_qry_req[:x_bytes_len]

                    pktCharEntropySeq_x_bytes.append(self.calcEntropy(Counter(bytes(trunc_qry_req))))

        # self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(scapy_qry_req)))
        #                           for pkt in self.cap if UDP in pkt and DNSQR in pkt
        #                           and len([DNSQR].qname) > 0 and pkt[UDP].dport==53]
        return pktCharEntropySeq_x_bytes

#---------------------------------#
######  IP Packet Methods    ######
#---------------------------------#
    def getIpPacketEntropy(self):
        '''
        :return:
        '''
        self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(pkt[IP])))
                                  for pkt in self.pktReader if IP in pkt]
        return self.pktCharEntropySeq

    def get_ip_pkt_lengths(self):
        #self.logger.debug("Packet Reader Filename: %s" % str(self.pktReader.filename))
        # for p in self.pktReader:
        #     self.logger.debug("lengths: %i" % len(p))
        self.pktIPLenSeq = [len(pkt[IP])for pkt in self.pktReader if IP in pkt]
        #self.logger.debug()

        return self.pktIPLenSeq

# #------------------------------------#
# ######   HTTP Related Methods   ######
# #------------------------------------#

    def getHttpReqBytesHex(self):
        '''
        Get the Bytes of only the HTTP Request characters in TCP packets
        that have a payload and have the destination port = 80
        Change them to hex and convert the byte array into a hex string (each pair of hex values represents a byte)
        :return:
        '''
        # self.pktCharSeq = [(pkt[IP][TCP][Raw].load).decode()  # <--- Will get HTTP Request strings in normal ascii text
        self.pktCharSeq = [b2a.hexlify(bytes(pkt[IP][TCP][Raw].load)).decode()
                                  for pkt in self.pktReader if TCP in pkt and Raw in pkt and pkt[TCP].dport == 80]
        return self.pktCharSeq

#     def get_ip_pkt_http_req_entropy(self):
#         '''
#         :return:
#         '''
#         self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(pkt[IP])))
#                                   for pkt in self.pktReader if TCP in pkt and pkt[TCP].dport == 80]
#         return self.pktCharEntropySeq
#
#     def get_ip_pkt_len_http_req(self):
#         self.specificPktLens = [len(pkt[IP])
#                                 for pkt in self.pktReader if TCP in pkt and pkt[TCP].dport == 80]
#         return self.specificPktLens
#
    def getHttpReqEntropy(self):
        '''
        Get the Entropy of only the HTTP Request characters in TCP packets
        that have a payload and have the destination port = 80
        :return:
        '''
        self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(pkt[IP][TCP][Raw].load)))
                                  for pkt in self.pktReader if TCP in pkt and Raw in pkt and pkt[TCP].dport == 80]
        return self.pktCharEntropySeq

#     def getCompressedHttpReqEntropy(self):
#         '''
#         Get the Entropy of only the HTTP Request characters in TCP packets
#         that have a payload and have the destination port = 80
#         :return:
#         '''
#         self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(zl.compress(pkt[IP][TCP][Raw].load))))
#                                   for pkt in self.pktReader if TCP in pkt and Raw in pkt and pkt[TCP].dport == 80]
#         return self.pktCharEntropySeq
#
#     def getHttpReqLen(self):
#         self.specificPktLens = [len(pkt[IP][TCP][Raw].load)
#                                 for pkt in self.pktReader if TCP in pkt and Raw in pkt and pkt[TCP].dport == 80]
#         return self.specificPktLens

# #---------------------------------####
# ###### HTTP-S related Methods     ####
# #---------------------------------####

    def getHttp_S_ReqBytesHex(self):
        '''
        Get the Bytes of only the HTTP-S Request characters in TCP packets
        that have a payload and have the destination port = 443
        Change them to hex and convert the byte array into a hex string (each pair of hex values represents a byte)
        :return:
        '''
        # self.pktCharSeq = [(pkt[IP][TCP][Raw].load).decode()  # <--- Will get HTTP Request strings in normal ascii text
        self.pktCharSeq = [b2a.hexlify(bytes(pkt[IP][TCP][Raw].load)).decode()
                                  for pkt in self.pktReader if TCP in pkt and Raw in pkt and pkt[TCP].dport == 443]
        return self.pktCharSeq

    def getHttp_S_ReqEntropy(self):
        '''
        Get the Entropy of only the HTTP-S Request characters in TCP packets
        that have a payload and have the destination port = 443
        :return:
        '''
        self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(pkt[IP][TCP][Raw].load)))
                                  for pkt in self.pktReader if TCP in pkt and Raw in pkt and pkt[TCP].dport == 443]
        return self.pktCharEntropySeq

# #---------------------------------#
# ###### POP3 related Methods   ######
# #---------------------------------#
    def getPop3ReqBytesHex(self):
        '''
        Get the Bytes of only the POP3 Request characters in TCP packets
        that have a payload and have the destination port = 110
        Change them to hex and convert the byte array into a hex string (each pair of hex values represents a byte)
        :return:
        '''
        # self.pktCharSeq = [(pkt[IP][TCP][Raw].load).decode()  # <--- Will get HTTP Request strings in normal ascii text
        self.pktCharSeq = [b2a.hexlify(bytes(pkt[IP][TCP][Raw].load)).decode()
                                  for pkt in self.pktReader if TCP in pkt and Raw in pkt and pkt[TCP].dport == 110]
        return self.pktCharSeq



# #---------------------------------#
# ###### FTP related Methods   ######
# #---------------------------------#

    def getFtpReqBytesHex(self):
        '''
        Get the Bytes of only the FTP Request characters in TCP packets
        that have a payload and have the destination port = 21
        Change them to hex and convert the byte array into a hex string (each pair of hex values represents a byte)
        :return:
        '''
        # self.pktCharSeq = [(pkt[IP][TCP][Raw].load).decode()  # <--- Will get HTTP Request strings in normal ascii text
        self.pktCharSeq = [b2a.hexlify(bytes(pkt[IP][TCP][Raw].load)).decode()
                                  for pkt in self.pktReader if TCP in pkt and Raw in pkt and pkt[TCP].dport == 21]
        return self.pktCharSeq

#     def getftpReqLen(self):
#         self.specificPktLens = [len(pkt[IP][TCP][Raw].load)
#                                 for pkt in self.pktReader if TCP in pkt and Raw in pkt and pkt[TCP].dport == 21]
#         return self.specificPktLens
#
#     def get_ip_pkt_len_ftp_req(self):
#         self.specificPktLens = [len(pkt[IP])
#                                 for pkt in self.pktReader if TCP in pkt and pkt[TCP].dport == 21]
#         return self.specificPktLens
#
#     def getFtpReqEntropy(self):
#         self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(pkt[IP][TCP][Raw].load)))
#                                   for pkt in self.pktReader if TCP in pkt and Raw in pkt and pkt[TCP].dport == 21]
#         return self.pktCharEntropySeq
#
#     def getCompressedFtpReqEntropy(self):
#         self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(zl.compress(pkt[IP][TCP][Raw].load))))
#                                   for pkt in self.pktReader if TCP in pkt and Raw in pkt and pkt[TCP].dport == 21]
#         return self.pktCharEntropySeq
#
#     def getFtpCommandChannelEntropy(self):
#         self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(pkt[IP][TCP][Raw].load)))
#                                   for pkt in self.pktReader if TCP in pkt and Raw in pkt
#                                   and (pkt[TCP].dport==21 or pkt[TCP].sport==21)]
#         return self.pktCharEntropySeq
#
#     def getFtpCommandChannelLens(self):
#         self.pktCharEntropySeq = [len(pkt[IP][TCP][Raw].load)
#                                   for pkt in self.pktReader if TCP in pkt and Raw in pkt
#                                   and (pkt[TCP].dport==21 or pkt[TCP].sport==21)]
#         return self.pktCharEntropySeq
#
#     def get_ftp_cmd_channel_pkt_entropy(self):
#         self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(pkt[IP])))
#                                   for pkt in self.pktReader
#                                   if TCP in pkt and (pkt[TCP].dport==21 or pkt[TCP].sport==21)]
#         return self.pktCharEntropySeq
#
#     def get_ip_pkt_ftp_req_entropy(self):
#         self.pktCharEntropySeq = [self.calcEntropy(Counter(bytes(pkt[IP])))
#                                   for pkt in self.pktReader if TCP in pkt and pkt[TCP].dport == 21]
#         return self.pktCharEntropySeq
#
#     def get_ftp_client_ip_pkt_lens(self, clientIpAddr):
#         self.specificPktLens = [len(pkt[IP])
#                                 for pkt in self.pktReader if TCP in pkt and pkt[IP].src == clientIpAddr]
#         return self.specificPktLens
#
#     def get_ftp_client_ip_pkt_entropy(self, clientIpAddr):
#         self.specificPktLens = [self.calcEntropy(Counter(bytes(pkt[IP])))
#                                 for pkt in self.pktReader if TCP in pkt and pkt[IP].src == clientIpAddr]
#         return self.specificPktLens

#--------------------------------------#
######   Plotting Related methods   ####
#--------------------------------------#
    def doPlot(self, yVariable, markercolor, plotTitle, xlbl, ylbl):
        '''
        Plot the points given from the given sequence
        '''

        self.fig = plt.figure()
        self.ax = plt.axes()

        #plt.plot(perPktCharEntropySeq, marker="+", markeredgecolor="red", linestyle="solid", color="blue")
        #self.ax.plot(yVariable, marker="+", markeredgecolor=markercolor, linestyle="None", color="blue")
        self.ax = self.fig.add_subplot(1,1,1)
        self.ax.plot(yVariable, marker="+", markeredgecolor=markercolor, linestyle="solid", color="blue")
        #plt.scatter(perPktCharEntropySeq)  # missing 'y' value ... but actually it's the x value that we need
        #self.fig.add_subplot()
        self.ax.set_title(plotTitle, size = 16)
        #self.fig.
        #self.fig.add_axes(xlabel=xlbl, ylabel=ylbl)
        self.ax.set_xlabel(xlbl, size=11)
        self.ax.set_ylabel(ylbl, size=11)
        #self.ax.xlabel("Packet Sequence (Time)", size=11)
        #self.ax.ylabel("Byte (Char) Entropy per packet", size=11)
        self.fig.show()
        #self.fig.savefig()
        self.fig.waitforbuttonpress(timeout= -1)
        #time.sleep(10)