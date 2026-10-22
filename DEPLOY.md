# Deploying Hotel Manager (VPS)

## Requirements
- Ubuntu 22.04+ VPS (2 GB RAM minimum)
- Docker + Docker Compose installed

## Steps
1. Clone the repo
2. Copy `docker-compose.yml` and adjust ports/volumes if needed
3. `docker compose up -d`
4. Open http://YOUR_IP:8069
5. Create database, install **Hotel Manager** and **Website**
6. Set company currency to NGN
7. Configure Paystack keys in Settings → Hotel Manager
8. Point a domain (or subdomain) to the server and (optional) add Nginx + SSL

## Pilot Hotel Tips
- Use a subdomain e.g. `booking.stanhotel.ng`
- Give the hotel manager and receptionist logins
- Load demo data first so they see how it looks
