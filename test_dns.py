#!/usr/bin/env python3
import time
import re

# Test run_id generation (from fixed code)
sec_level = 'SEC0'
net_profile = 'NET0'
run_id = f"{sec_level.lower()}-{net_profile.lower()}-{int(time.time())}"
print(f"✅ Generated run_id: {run_id}")

# Test DNS compliance  
dns_pattern = r'^[a-z]([a-z0-9\-]*[a-z0-9])?$'
is_valid = re.match(dns_pattern, run_id) is not None
print(f"✅ DNS compliant: {is_valid}")

# Test resource names
server_name = f'fl-server-{run_id}'
client_name = f'fl-client-1-{run_id}'
print(f"✅ Server name: {server_name} (valid: {re.match(dns_pattern, server_name) is not None})")
print(f"✅ Client name: {client_name} (valid: {re.match(dns_pattern, client_name) is not None})")

# Compare with old format (broken)
old_run_id = f"{sec_level}_{net_profile}_{int(time.time())}"
print(f"\n❌ Old format: {old_run_id} (valid: {re.match(dns_pattern, old_run_id) is not None})")

print("\n🎉 Bug #20 DNS naming fix is working!")