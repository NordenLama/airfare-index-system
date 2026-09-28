#!/bin/bash
# Airfare Index System - Unified Startup Script
# Starts: Main Dashboard (port 8000) + Backend API (port 8001)

set -e

PROJECT_DIR="/Users/suramyamondal/airfare-index-system"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Airfare Index System...${NC}"
echo ""

# Kill any existing servers on our ports
echo -e "${YELLOW}🔄 Stopping any existing servers on ports 8000, 8001...${NC}"
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
sleep 1

# Check if virtual environment exists
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo -e "${RED}❌ Virtual environment not found at $PROJECT_DIR/.venv${NC}"
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$PROJECT_DIR/.venv"
    "$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
fi

# Use the venv Python directly
PYTHON="$PROJECT_DIR/.venv/bin/python"
UVICORN="$PROJECT_DIR/.venv/bin/uvicorn"

# Initialize database
echo -e "${GREEN}📊 Initializing database...${NC}"
cd "$PROJECT_DIR"
python -c "from database.db_manager import init_db; init_db()"

# Build frontend if dist doesn't exist
echo -e "${GREEN}📦 Checking frontend build...${NC}"
if [ ! -d "$PROJECT_DIR/frontend/dist" ]; then
    echo -e "   ${YELLOW}Building frontend...${NC}"
    cd "$PROJECT_DIR/frontend" && npm run build
else
    echo -e "   ${GREEN}✅ Frontend already built${NC}"
fi

# 1. Start Main API Server (port 8001) - The primary API with auth
echo -e "${GREEN}1️⃣  Starting Main API Server on port 8001...${NC}"
cd "$PROJECT_DIR"
"$UVICORN" api.main:app --host 0.0.0.0 --port 8001 > /tmp/api_server.log 2>&1 &
API_PID=$!
echo "   PID: $API_PID"

# Wait for API
for i in {1..30}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Main API Server ready!${NC}"
        break
    fi
    sleep 1
done

# 2. Start Prototype Dashboard Server (port 8000) - Full featured prototype
echo -e "${GREEN}2️⃣  Starting Prototype Dashboard on port 8000...${NC}"
cd "$PROJECT_DIR"
"$PYTHON" prototype_server.py > /tmp/prototype_server.log 2>&1 &
DASHBOARD_PID=$!
echo "   PID: $DASHBOARD_PID"

# Wait for Dashboard
for i in {1..30}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Prototype Dashboard ready!${NC}"
        break
    fi
    sleep 1
done

# 3. Start Frontend Dev Server (port 5173) - For Live Share / Vite
echo -e "${GREEN}3️⃣  Starting Frontend Dev Server on port 5173...${NC}"
cd "$PROJECT_DIR/frontend"
npx vite --host 0.0.0.0 --port 5173 > /tmp/vite_dev.log 2>&1 &
VITE_PID=$!
echo "   PID: $VITE_PID"

for i in {1..15}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Frontend Dev Server ready!${NC}"
        break
    fi
    sleep 1
done

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ ALL SERVERS RUNNING!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}📍 ACCESS POINTS:${NC}"
echo -e "   ${BLUE}🎯 Prototype Dashboard (Full Features):${NC} http://localhost:8000"
echo -e "   ${BLUE}🔧 Main API Server (with Auth):${NC} http://localhost:8001"
echo -e "   ${BLUE}📖 API Docs (Swagger):${NC} http://localhost:8001/docs"
echo -e "   ${BLUE}🎨 Frontend Dev Server (Live Share):${NC} http://localhost:5173"
echo ""
echo -e "${YELLOW}🔐 OTP DEMO CREDENTIALS:${NC}"
echo -e "   Phone: Any 10-digit number (e.g., ${GREEN}9876543210${NC})"
echo -e "   OTP:   ${GREEN}123456${NC} (always works in demo mode)"
echo ""
echo -e "${YELLOW}🔐 OTP DEMO CREDENTIALS:${NC}"
echo -e "   Phone: Any 10-digit number (e.g., ${GREEN}9876543210${NC})"
echo -e "   OTP:   ${GREEN}123456${NC} (always works in demo mode)"
echo ""
echo -e "${YELLOW}✨ FEATURES IN PROTOTYPE DASHBOARD (http://localhost:8000):${NC}"
echo ""
echo -e "   ${GREEN}National Airfare Index${NC} (Laspeyres, real-time)"
echo -e "   ${GREEN}Matrix Heatmap${NC} (Origin-Destination fare matrix)"
echo -e "   ${GREEN}OTP Authentication${NC} (Sign In / Sign Up button)"
echo -e "   ${GREEN}Fare Alerts${NC} (Subscribe after OTP verification)"
echo -e "   ${GREEN}ML Forecasting${NC} (45-day predictions, citizen advisory)"
echo -e "   ${GREEN}Surveillance Monitor${NC} (Carrier daemons, corridor health)"
echo -e "   ${GREEN}Reports & DGCA Backtest${NC} (90-day backtest)"
echo -e "   ${GREEN}AI Chat Assistant${NC} (Ask about APIx, ML, SMS, scraper)"
echo -e "   ${GREEN}Trigger Live Scrape${NC} (Refresh route data)"
echo -e "   ${GREEN}Tax Separation & Cleansing${NC} (Z-score, tax breakdown)"
echo -e "   ${GREEN}Lead-Time Elasticity${NC} (T+1 to T+45 multipliers)"
echo ""
echo -e "${YELLOW}🔧 MAIN API ENDPOINTS (http://localhost:8001/api/v1):${NC}"
echo -e "   • GET  /analytics - Full analytics (price index, volatility, rankings)"
echo -e "   • GET  /analytics/timeseries - Index time series"
echo -e "   • GET  /analytics/routes/recommended - DGCA recommended routes"
echo -e "   • GET  /analytics/data-quality - Data quality report"
echo -e "   • GET  /dashboard/summary - Dashboard summary"
echo -e "   • GET  /routes - Route analysis"
echo -e "   • GET  /quality - Quality assessment"
echo -e "   • GET  /routes/{route}/context - News context for route"
echo -e "   • POST /index/calculate - Calculate index"
echo -e "   • POST /forecast/* - Forecasting endpoints"
echo ""
echo -e "${YELLOW}📝 LOGS:${NC}"
echo -e "   Prototype: ${BLUE}tail -f /tmp/prototype_server.log${NC}"
echo -e "   API:       ${BLUE}tail -f /tmp/api_server.log${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# Keep running
trap "echo -e '\n${YELLOW}🛑 Stopping all servers...${NC}'; kill $DASHBOARD_PID $API_PID $VITE_PID 2>/dev/null; echo -e '${GREEN}✅ All servers stopped${NC}'" EXIT
wait $DASHBOARD_PID $API_PID $VITE_PID