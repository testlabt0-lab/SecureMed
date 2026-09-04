"""
Port Scanner utility.

Security requirement #2: أداة مسح المنافذ (Port Scanner)
Performs TCP port scanning on target hosts (localhost/infrastructure by default).
"""
import socket 
import time 
import ipaddress 
import logging 
from concurrent .futures import ThreadPoolExecutor ,as_completed 
from dataclasses import dataclass ,asdict 
from typing import List ,Dict ,Optional 
from datetime import datetime 

logger =logging .getLogger ('security')

# Comment_350
COMMON_PORTS ={
20 :'FTP-Data',
21 :'FTP',
22 :'SSH',
23 :'Telnet',
25 :'SMTP',
53 :'DNS',
80 :'HTTP',
110 :'POP3',
143 :'IMAP',
161 :'SNMP',
162 :'SNMP-Trap',
389 :'LDAP',
443 :'HTTPS',
445 :'SMB',
465 :'SMTPS',
587 :'SMTP-Submission',
636 :'LDAPS',
993 :'IMAPS',
995 :'POP3S',
1433 :'MSSQL',
1521 :'Oracle',
3306 :'MySQL',
3389 :'RDP',
5432 :'PostgreSQL',
5900 :'VNC',
6379 :'Redis',
8080 :'HTTP-Alt',
8443 :'HTTPS-Alt',
9090 :'Prometheus',
27017 :'MongoDB',
}

# Comment_351
HIGH_RISK_PORTS =[23 ,445 ,1433 ,3389 ,5900 ,6379 ,27017 ]


@dataclass 
class PortResult :
    port :int 
    service :str 
    state :str # Comment_352
    risk_level :str # Comment_353
    banner :Optional [str ]=None 


@dataclass 
class ScanResult :
    target :str 
    scan_time :str 
    duration_seconds :float 
    ports_scanned :int 
    open_ports :int 
    results :List [Dict ]
    summary :str 
    risk_assessment :str 


class PortScanner :
    """
    TCP Connect scanner - uses Python sockets to scan ports.
    Designed to scan infrastructure (localhost/allowed hosts) for security audits.
    """

    def __init__ (self ,timeout :float =1.0 ,max_workers :int =50 ):
        self .timeout =timeout 
        self .max_workers =max_workers 

    def scan_port (self ,host :str ,port :int )->PortResult :
        """Scan a single port on host."""
        service =COMMON_PORTS .get (port ,'Unknown')
        risk_level =self ._assess_risk (port )

        sock =None 
        try :
            sock =socket .socket (socket .AF_INET ,socket .SOCK_STREAM )
            sock .settimeout (self .timeout )
            result =sock .connect_ex ((host ,port ))

            if result ==0 :
            # Comment_354
                banner =self ._grab_banner (sock ,port )
                return PortResult (
                port =port ,service =service ,
                state ='open',risk_level =risk_level ,banner =banner 
                )
            else :
                return PortResult (
                port =port ,service =service ,
                state ='closed',risk_level ='info'
                )
        except socket .timeout :
            return PortResult (
            port =port ,service =service ,
            state ='filtered',risk_level ='info'
            )
        except Exception as e :
            logger .debug (f"Scan error on {host }:{port } - {e }")
            return PortResult (
            port =port ,service =service ,
            state ='error',risk_level ='info'
            )
        finally :
            if sock :
                try :
                    sock .close ()
                except Exception :
                    pass 

    def scan_host (self ,host :str ,ports :Optional [List [int ]]=None )->ScanResult :
        """Scan multiple ports on a host in parallel."""
        # Comment_355
        if not self ._is_scan_allowed (host ):
            raise ValueError (f"غير مسموح بمسح المضيف: {host }")

        if ports is None :
            ports =list (COMMON_PORTS .keys ())

        start_time =time .time ()
        results :List [PortResult ]=[]

        with ThreadPoolExecutor (max_workers =self .max_workers )as executor :
            future_to_port ={
            executor .submit (self .scan_port ,host ,port ):port 
            for port in ports 
            }
            for future in as_completed (future_to_port ):
                results .append (future .result ())

                # Comment_356
        results .sort (key =lambda r :r .port )

        # Comment_357
        open_ports =[r for r in results if r .state =='open']
        high_risk_open =[r for r in open_ports if r .port in HIGH_RISK_PORTS ]

        duration =time .time ()-start_time 

        risk_assessment =self ._generate_risk_assessment (open_ports ,high_risk_open )

        return ScanResult (
        target =host ,
        scan_time =datetime .utcnow ().isoformat ()+'Z',
        duration_seconds =round (duration ,2 ),
        ports_scanned =len (results ),
        open_ports =len (open_ports ),
        results =[asdict (r )for r in results ],
        summary =f"تم فحص {len (results )} منفذ، {len (open_ports )} مفتوح، "
        f"{len (high_risk_open )} عالي الخطورة",
        risk_assessment =risk_assessment ,
        )

    def _grab_banner (self ,sock :socket .socket ,port :int )->Optional [str ]:
        """Try to grab service banner."""
        try :
            if port in (80 ,8080 ):
                sock .send (b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
            elif port ==443 :
                return 'HTTPS'
            else :
                pass 

            data =sock .recv (1024 )
            if data :
                return data .decode ('utf-8',errors ='ignore')[:100 ].strip ()
        except Exception :
            pass 
        return None 

    def _assess_risk (self ,port :int )->str :
        """Assess risk level of a port."""
        if port in HIGH_RISK_PORTS :
            return 'critical'
        if port in [21 ,23 ,161 ,389 ,5900 ]:
            return 'high'
        if port in [25 ,110 ,143 ,8080 ]:
            return 'medium'
        if port in [80 ,443 ,22 ,5432 ,3306 ]:
            return 'low'
        return 'info'

    def _is_scan_allowed (self ,host :str )->bool :
        """Check if scanning this host is allowed (security)."""
        try :
            ip =ipaddress .ip_address (host )
            # Comment_358
            return ip .is_private or ip .is_loopback 
        except ValueError :
        # Comment_359
            return host in ['localhost','127.0.0.1','0.0.0.0']

    def _generate_risk_assessment (self ,open_ports ,high_risk_open )->str :
        """Generate human-readable risk assessment."""
        if not open_ports :
            return "✅ لا توجد منافذ مفتوحة. مستوى الأمان ممتاز."

        assessment_parts =[]
        if high_risk_open :
            port_list =', '.join (f"{p .port } ({p .service })"for p in high_risk_open )
            assessment_parts .append (
            f"⚠️ تحذير حرج: المنافذ التالية عالية الخطورة مفتوحة: {port_list }. "
            f"يفضل إغلاقها فوراً."
            )

        exposed_db =[p for p in open_ports if p .port in [3306 ,5432 ,27017 ,6379 ]]
        if exposed_db :
            assessment_parts .append (
            "⚠️ قاعدة البيانات مكشوفة! تأكد من أن الوصول مقيد بـ localhost فقط."
            )

        if not assessment_parts :
            return "✅ المنافذ المفتوحة طبيعية ومتوقعة لمخدم ويب."

        return ' '.join (assessment_parts )


        # Comment_360
def scan_host_ports (host :str ='localhost',ports :Optional [List [int ]]=None )->Dict :
    """Run a port scan and return results as dict."""
    scanner =PortScanner ()
    result =scanner .scan_host (host ,ports )
    return asdict (result )
