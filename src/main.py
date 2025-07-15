#!/usr/bin/env python3

import boto3
import requests
import json
import os
import sys
import logging
import logging.handlers
from datetime import datetime, timedelta

# Configurazione logging
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Rimuovi handler esistenti
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Console handler (sempre attivo)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Syslog handler (opzionale)
    syslog_server = os.getenv('SYSLOG_SERVER')
    syslog_port = int(os.getenv('SYSLOG_PORT', '514'))
    
    if syslog_server:
        try:
            syslog_handler = logging.handlers.SysLogHandler(
                address=(syslog_server, syslog_port),
                facility=logging.handlers.SysLogHandler.LOG_DAEMON
            )
            syslog_formatter = logging.Formatter('aws-sg-manager: %(levelname)s - %(message)s')
            syslog_handler.setFormatter(syslog_formatter)
            logger.addHandler(syslog_handler)
            logger.info(f"Syslog enabled: {syslog_server}:{syslog_port}")
        except Exception as e:
            logger.warning(f"Failed to setup syslog: {e}")
    
    return logger

class SecurityGroupManager:
    def __init__(self):
        self.logger = setup_logging()
        self.ec2 = boto3.client('ec2')
        self.security_group_id = os.getenv('SECURITY_GROUP_ID')
        self.port = int(os.getenv('PORT', '22'))
        self.protocol = os.getenv('PROTOCOL', 'tcp')
        self.description = os.getenv('RULE_DESCRIPTION', 'Dynamic IP access')
        self.force_check_hours = int(os.getenv('FORCE_CHECK_HOURS', '24'))  # Default: 24 ore
        
        # File per persistenza dati
        self.ip_file = '/data/current_ip.txt'
        self.timestamp_file = '/data/last_update.txt'

        if not self.security_group_id:
            raise ValueError("SECURITY_GROUP_ID environment variable is required")

    def get_current_public_ip(self):
        """Ottiene l'IP pubblico corrente"""
        try:
            response = requests.get('https://api.ipify.org', timeout=10)
            return response.text.strip()
        except Exception as e:
            self.logger.error(f"Error getting public IP: {e}")
            return None

    def get_saved_ip(self):
        """Legge l'IP salvato dal file"""
        if os.path.exists(self.ip_file):
            try:
                with open(self.ip_file, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                self.logger.error(f"Error reading IP file: {e}")
        return None

    def save_ip(self, ip):
        """Salva l'IP corrente nel file"""
        try:
            os.makedirs(os.path.dirname(self.ip_file), exist_ok=True)
            with open(self.ip_file, 'w') as f:
                f.write(ip)
            self.logger.info(f"IP {ip} saved to file")
        except Exception as e:
            self.logger.error(f"Error saving IP to file: {e}")

    def get_last_update_timestamp(self):
        """Legge il timestamp dell'ultimo aggiornamento del security group"""
        if os.path.exists(self.timestamp_file):
            try:
                with open(self.timestamp_file, 'r') as f:
                    timestamp_str = f.read().strip()
                    return datetime.fromisoformat(timestamp_str)
            except Exception as e:
                self.logger.error(f"Error reading timestamp file: {e}")
        return None

    def save_update_timestamp(self):
        """Salva il timestamp dell'aggiornamento corrente"""
        try:
            os.makedirs(os.path.dirname(self.timestamp_file), exist_ok=True)
            with open(self.timestamp_file, 'w') as f:
                f.write(datetime.now().isoformat())
            self.logger.info(f"Update timestamp saved")
        except Exception as e:
            self.logger.error(f"Error saving timestamp: {e}")

    def should_force_check(self):
        """Determina se è necessario un controllo forzato del security group"""
        last_update = self.get_last_update_timestamp()
        if not last_update:
            return True  # Prima esecuzione
        
        time_since_update = datetime.now() - last_update
        force_check_needed = time_since_update >= timedelta(hours=self.force_check_hours)
        
        if force_check_needed:
            self.logger.info(f"Force check needed: {time_since_update} > {self.force_check_hours} hours")
        
        return force_check_needed

    def ip_exists_in_sg(self, ip):
        """Controlla se l'IP è già presente nel security group"""
        try:
            response = self.ec2.describe_security_groups(GroupIds=[self.security_group_id])

            for rule in response['SecurityGroups'][0]['IpPermissions']:
                if (rule.get('IpProtocol') == self.protocol and 
                    rule.get('FromPort') == self.port and 
                    rule.get('ToPort') == self.port):

                    for ip_range in rule.get('IpRanges', []):
                        if ip_range.get('CidrIp') == f"{ip}/32":
                            return True
            return False

        except Exception as e:
            self.logger.error(f"Error checking IP in security group: {e}")
            return False

    def add_ip_to_sg(self, ip):
        """Aggiunge l'IP al security group"""
        try:
            self.ec2.authorize_security_group_ingress(
                GroupId=self.security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': self.protocol,
                        'FromPort': self.port,
                        'ToPort': self.port,
                        'IpRanges': [
                            {
                                'CidrIp': f"{ip}/32",
                                'Description': self.description
                            }
                        ]
                    }
                ]
            )
            self.logger.info(f"IP {ip} added to security group {self.security_group_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error adding IP to security group: {e}")
            return False

    def remove_ip_from_sg(self, ip):
        """Rimuove l'IP dal security group"""
        try:
            self.ec2.revoke_security_group_ingress(
                GroupId=self.security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': self.protocol,
                        'FromPort': self.port,
                        'ToPort': self.port,
                        'IpRanges': [
                            {
                                'CidrIp': f"{ip}/32"
                            }
                        ]
                    }
                ]
            )
            self.logger.info(f"IP {ip} removed from security group {self.security_group_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error removing IP from security group: {e}")
            return False

    def run(self):
        """Esegue la logica principale con ottimizzazioni per evitare chiamate AWS non necessarie"""
        self.logger.info(f"[{datetime.now()}] Starting IP check...")

        # Ottieni IP pubblico corrente
        current_ip = self.get_current_public_ip()
        if not current_ip:
            self.logger.error("Failed to get current public IP")
            return False

        self.logger.info(f"Current public IP: {current_ip}")

        # Leggi l'IP precedente dal file
        saved_ip = self.get_saved_ip()
        
        # Determina se è necessario controllare/aggiornare il security group
        ip_changed = saved_ip != current_ip
        force_check_needed = self.should_force_check()
        
        if not ip_changed and not force_check_needed:
            self.logger.info(f"IP unchanged ({current_ip}) and no force check needed. Skipping AWS calls.")
            return True
        
        if ip_changed:
            self.logger.info(f"IP changed from {saved_ip} to {current_ip}")
        
        if force_check_needed:
            self.logger.info("Performing forced security group verification")

        # Controlla se l'IP è già presente nel security group
        if self.ip_exists_in_sg(current_ip):
            self.logger.info("IP already exists in security group")
            if ip_changed:
                # IP cambiato ma già presente nel SG, salva il nuovo IP
                self.save_ip(current_ip)
            # Aggiorna timestamp per reset del timer di force check
            self.save_update_timestamp()
            return True

        # Se arriviamo qui, l'IP non è presente nel security group
        self.logger.info("IP not found in security group, updating...")

        # Se c'è un IP salvato e diverso da quello corrente, rimuovilo
        if saved_ip and saved_ip != current_ip:
            self.logger.info(f"Removing old IP: {saved_ip}")
            self.remove_ip_from_sg(saved_ip)

        # Aggiungi il nuovo IP
        self.logger.info(f"Adding new IP: {current_ip}")
        if self.add_ip_to_sg(current_ip):
            self.save_ip(current_ip)
            self.save_update_timestamp()
            self.logger.info("IP update completed successfully")
            return True
        else:
            self.logger.error("Failed to add new IP")
            return False

def main():
    logger = None
    try:
        manager = SecurityGroupManager()
        logger = manager.logger
        success = manager.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        if logger:
            logger.error(f"Fatal error: {e}")
        else:
            # Fallback se il logger non è ancora disponibile
            print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
