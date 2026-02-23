# MySQL Connection Troubleshooting Guide

## 🔴 Current Problem: Connection Timeout (Port Blocked)

### Error Message
```
Error connecting to MySDB: 2003: Can't connect to MySQL server on 'qatra.sa:3306'
Errno 10060: A connection attempt failed because the connected party did not 
properly respond after a period of time
```

### Root Cause
**MySQL port 3306 is blocked or remote access is disabled** on the server `qatra.sa`.

---

## 🧪 Test Results

### Network Connectivity Test
```powershell
Test-NetConnection -ComputerName qatra.sa -Port 3306
```

**Results:**
- ✅ **DNS Resolution**: Success (multiple IPs found)
- ✅ **Ping Test**: Success (32ms response time)
- ❌ **TCP Port 3306**: **FAILED** (Connection refused/timeout)

**IPs Detected:**
- `172.67.144.169` (Cloudflare CDN)
- `104.21.95.115` (Cloudflare CDN)
- IPv6 addresses also present

**Conclusion:** Server is behind Cloudflare and MySQL port is not publicly accessible.

---

## ✅ Solutions (In Order of Preference)

### Solution 1: Request Remote MySQL Access from Host ⭐ **RECOMMENDED**

#### Step 1: Find Your Odoo Server IP
Your Odoo server's public IP is: **`31.167.155.172`**

#### Step 2: Contact Hosting Provider
Use the template in `MYSQL_CONNECTION_REQUEST.txt` to request:
1. Enable remote MySQL access
2. Whitelist IP: `31.167.155.172`
3. Provide correct MySQL hostname (might be different from `qatra.sa`)

#### Step 3: Common Hosting Provider Instructions

**cPanel Hosting:**
1. Log into cPanel
2. Go to **"Remote MySQL"** or **"Remote Database Access"**
3. Add IP: `31.167.155.172`
4. Click **"Add Host"**

**Plesk Hosting:**
1. Go to **Tools & Settings** > **MySQL Database Servers**
2. Click on your database server
3. Enable **"Allow remote connections"**
4. Add IP to whitelist

**AWS RDS:**
1. Go to RDS Console
2. Select your database instance
3. Click **"Modify"**
4. Under **Security Group**, add inbound rule:
   - Type: MySQL/Aurora
   - Port: 3306
   - Source: `31.167.155.172/32`

**Azure Database:**
1. Go to your MySQL server
2. Select **"Connection security"**
3. Add firewall rule:
   - Rule name: `OdooServer`
   - Start IP: `31.167.155.172`
   - End IP: `31.167.155.172`

#### Step 4: Update Odoo Credential
After remote access is enabled:
```
Host: qatra.sa  (or the hostname provided by your host)
Username: your_mysql_user
Password: ********
Database: your_database_name
```

**Important:** Remove `:3306` from the hostname field!

---

### Solution 2: SSH Tunnel (If Direct Access Not Available)

If your hosting provider doesn't allow direct MySQL access, but you have SSH access:

#### Windows (using PuTTY)
1. Open PuTTY
2. Session: `your_user@qatra.sa`
3. Go to **Connection > SSH > Tunnels**
4. Add tunnel:
   - Source port: `3307`
   - Destination: `localhost:3306`
   - Click **"Add"**
5. Connect and leave PuTTY running

#### In Odoo Credential:
```
Host: localhost
Port: 3307  (Note: You'll need to modify the code to accept custom port)
Username: your_mysql_user
Password: ********
Database: your_database_name
```

**Limitation:** PuTTY must remain open while Odoo syncs.

---

### Solution 3: Check for Different MySQL Hostname

Your MySQL server might not be at `qatra.sa`. Ask your host for the correct hostname:

**Common patterns:**
- `db.qatra.sa`
- `mysql.qatra.sa`
- `qatra.sa` (web) vs `db-server.qatra.sa` (database)
- Private IP: `10.x.x.x` or `192.168.x.x` (if on same network)

**Test different hostnames:**
```powershell
Test-NetConnection -ComputerName db.qatra.sa -Port 3306
Test-NetConnection -ComputerName mysql.qatra.sa -Port 3306
```

---

### Solution 4: Verify MySQL User Permissions

Even with remote access enabled, the MySQL user must be granted remote permissions:

```sql
-- Connect to MySQL as root/admin
mysql -u root -p

-- Grant access from specific IP
GRANT ALL PRIVILEGES ON your_database.* 
TO 'your_user'@'31.167.155.172' 
IDENTIFIED BY 'your_password';

-- Or grant from any IP (less secure)
GRANT ALL PRIVILEGES ON your_database.* 
TO 'your_user'@'%' 
IDENTIFIED BY 'your_password';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify
SELECT user, host FROM mysql.user WHERE user='your_user';
```

**Expected output:**
```
+----------+------------------+
| user     | host             |
+----------+------------------+
| your_user| 31.167.155.172  |
+----------+------------------+
```

---

### Solution 5: MySQL Server Configuration (If You Have Root Access)

If you manage the MySQL server yourself:

#### Edit MySQL Configuration File

**Linux:** `/etc/mysql/my.cnf` or `/etc/mysql/mysql.conf.d/mysqld.cnf`

**Windows:** `C:\ProgramData\MySQL\MySQL Server X.X\my.ini`

#### Change bind-address

```ini
[mysqld]
# OLD (local only)
bind-address = 127.0.0.1

# NEW (allow external)
bind-address = 0.0.0.0
```

#### Restart MySQL

**Linux:**
```bash
sudo systemctl restart mysql
# or
sudo service mysql restart
```

**Windows:**
```powershell
Restart-Service MySQL80  # Or your MySQL service name
```

#### Open Firewall Port

**Linux (UFW):**
```bash
sudo ufw allow from 31.167.155.172 to any port 3306
sudo ufw reload
```

**Windows Firewall:**
```powershell
New-NetFirewallRule -DisplayName "MySQL Remote" -Direction Inbound -Protocol TCP -LocalPort 3306 -RemoteAddress 31.167.155.172 -Action Allow
```

---

## 🔍 Diagnostic Commands

### Test MySQL Port Accessibility
```powershell
Test-NetConnection -ComputerName qatra.sa -Port 3306
```

**Success looks like:**
```
TcpTestSucceeded : True
```

**Failure looks like:**
```
TcpTestSucceeded : False
WARNING: TCP connect to (x.x.x.x : 3306) failed
```

### Get Your Public IP
```powershell
(Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing).Content
```

### Test from Odoo Server
After changes are made, test in Odoo:
1. Go to **MySDB Dashboard** > **Credentials**
2. Update hostname (remove `:3306` if present)
3. Click **"Test Connection"** or **"Connect"**

---

## 📋 Pre-Connection Checklist

Before attempting to connect, verify:

- [ ] MySQL hostname is correct (no `/phpmyadmin`, no `:3306`)
- [ ] Remote MySQL access is enabled on server
- [ ] IP `31.167.155.172` is whitelisted
- [ ] MySQL user has remote access permissions (`@'31.167.155.172'` or `@'%'`)
- [ ] Port 3306 is open in server firewall
- [ ] MySQL server is listening on `0.0.0.0` (not just `127.0.0.1`)
- [ ] No intermediate firewall blocking the connection

---

## 🆘 Still Not Working?

### Gather Information

1. **Hosting Provider Details:**
   - Company name: _______________
   - Hosting type: Shared / VPS / Dedicated / Cloud

2. **MySQL Server Location:**
   - Same server as website? Yes / No
   - If different, hostname: _______________

3. **SSH Access:**
   - Do you have SSH access? Yes / No
   - If yes, hostname: _______________

4. **Error Messages:**
   - Copy the full error from Odoo
   - Copy results of `Test-NetConnection`

5. **Test Results:**
```powershell
# Run these and share results
Test-NetConnection -ComputerName qatra.sa -Port 3306 -InformationLevel Detailed
Test-NetConnection -ComputerName qatra.sa -Port 22  # SSH port
nslookup qatra.sa
```

---

## 📞 Contact Your Hosting Provider

**Template Email:**

See `MYSQL_CONNECTION_REQUEST.txt` for a ready-to-send email template.

**Key Information to Provide:**
- Your IP: `31.167.155.172`
- Required port: `3306`
- Purpose: Remote database connection for Odoo ERP
- Security: Only whitelisting specific IP (not public access)

---

## ✅ Success Criteria

You'll know it's working when:

1. **Network test succeeds:**
```powershell
Test-NetConnection -ComputerName qatra.sa -Port 3306
# Result: TcpTestSucceeded = True
```

2. **Odoo connection works:**
   - No timeout errors
   - "Connected" status in Odoo credential
   - Can fetch table structure

3. **Data sync completes:**
   - No connection errors during sync
   - Data appears in Odoo

---

## 🔐 Security Best Practices

Once connected:

1. **Use Strong Passwords:** 16+ characters with symbols
2. **Limit IP Access:** Only whitelist your Odoo server IP
3. **Use SSL/TLS:** If supported, enable encrypted connections
4. **Limited Permissions:** Grant only necessary database permissions
5. **Monitor Connections:** Check MySQL logs for unusual access
6. **Regular Updates:** Keep MySQL and Odoo updated

---

## 📚 Additional Resources

- [MySQL Remote Access Documentation](https://dev.mysql.com/doc/)
- [Odoo MySQL Connector Module](https://apps.odoo.com/)
- [MySQL Firewall Configuration](https://dev.mysql.com/doc/refman/8.0/en/firewall.html)
- [Test MySQL Connection Online](https://www.connectionstrings.com/mysql/)

---

## 📝 Change Log

| Date | Issue | Resolution |
|------|-------|------------|
| 2026-01-14 | `Errno 11001` DNS failure | Fixed hostname format (removed `/phpmyadmin`) |
| 2026-01-14 | `Errno 10060` Connection timeout | Identified port 3306 blocked, awaiting remote access |

---

**Last Updated:** January 14, 2026  
**Your Odoo Server IP:** 31.167.155.172  
**Target MySQL Host:** qatra.sa  
**Status:** ⏳ Waiting for remote MySQL access to be enabled


