/* ==========================================
   SMART BAKERY AI - MAIN JS CONTROLLER
   ========================================== */

// Helper to format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

// Global chart variables to allow updating/destroying
let salesTrendChartInst = null;
let forecastActualChartInst = null;

// Load dashboard statistics and render charts
async function loadDashboardData() {
    const accuracyKPI = document.getElementById('kpi-accuracy');
    const wastageKPI = document.getElementById('kpi-wastage');
    const lowStockKPI = document.getElementById('kpi-low-stock');
    
    const wastageTbody = document.getElementById('wastage-table-body');
    const lowStockTbody = document.getElementById('low-stock-table-body');

    try {
        const response = await fetch('/api/dashboard_data');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Failed to load dashboard data");
        }

        // 1. Update KPI Values
        if (accuracyKPI) accuracyKPI.textContent = data.accuracy_score;
        
        let totalWastage = 0;
        if (data.wastage_report) {
            totalWastage = data.wastage_report.reduce((sum, item) => sum + item.wastage, 0);
        }
        if (wastageKPI) wastageKPI.textContent = totalWastage;
        
        const lowStockCount = data.low_stock ? data.low_stock.length : 0;
        if (lowStockKPI) {
            lowStockKPI.textContent = lowStockCount;
            const stockIcon = document.getElementById('kpi-stock-icon');
            if (lowStockCount > 0 && stockIcon) {
                stockIcon.classList.add('glowing-text-danger');
            }
        }

        // 2. Populate Wastage Table
        if (wastageTbody) {
            wastageTbody.innerHTML = '';
            if (data.wastage_report && data.wastage_report.length > 0) {
                data.wastage_report.forEach(item => {
                    const totalBake = item.forecast;
                    const efficiency = totalBake > 0 
                        ? ((item.actual / totalBake) * 100).toFixed(1) + '%' 
                        : '100.0%';
                        
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td class="font-semibold">${item.item_name}</td>
                        <td class="text-right font-mono">${item.forecast}</td>
                        <td class="text-right font-mono">${item.actual}</td>
                        <td class="text-right font-mono text-pink font-semibold">${item.wastage}</td>
                        <td class="text-right font-mono text-cyan font-bold">${efficiency}</td>
                    `;
                    wastageTbody.appendChild(tr);
                });
            } else {
                wastageTbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No products found.</td></tr>`;
            }
        }

        // 3. Populate Low Stock Widget Table
        if (lowStockTbody) {
            lowStockTbody.innerHTML = '';
            if (data.low_stock && data.low_stock.length > 0) {
                data.low_stock.forEach(item => {
                    const tr = document.createElement('tr');
                    tr.className = 'row-highlight-danger';
                    tr.innerHTML = `
                        <td class="font-semibold text-orange">${item.name}</td>
                        <td class="text-right font-mono font-bold text-danger">${item.stock_qty} ${item.unit}</td>
                        <td class="text-right font-mono">${item.threshold} ${item.unit}</td>
                        <td class="text-center">
                            <span class="badge-status badge-status-danger glowing-text-danger">
                                <i class="fa-solid fa-triangle-exclamation"></i> Urgent
                            </span>
                        </td>
                    `;
                    lowStockTbody.appendChild(tr);
                });
            } else {
                lowStockTbody.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center text-success py-4">
                            <i class="fa-solid fa-circle-check"></i> All raw materials fully stocked!
                        </td>
                    </tr>
                `;
            }
        }

        // 4. Render Sales & Revenue Trend Chart
        if (data.sales_trend && data.sales_trend.length > 0) {
            renderSalesTrendChart(data.sales_trend);
        }

        // 5. Render Forecast vs Actual Chart
        if (data.forecast_vs_actual && data.forecast_vs_actual.length > 0) {
            renderForecastActualChart(data.forecast_vs_actual);
        }

    } catch (error) {
        console.error("Dashboard error:", error);
    }
}

// Render Sales Trend Chart (Line Chart with dual axis)
function renderSalesTrendChart(trendData) {
    const ctx = document.getElementById('salesTrendChart');
    if (!ctx) return;

    if (salesTrendChartInst) {
        salesTrendChartInst.destroy();
    }

    const labels = trendData.map(d => d.date);
    const qtys = trendData.map(d => d.total_qty);
    const revenues = trendData.map(d => d.total_revenue);

    salesTrendChartInst = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Units Sold',
                    data: qtys,
                    borderColor: '#00f0ff',
                    backgroundColor: 'rgba(0, 240, 255, 0.05)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'yQty'
                },
                {
                    label: 'Revenue ($)',
                    data: revenues,
                    borderColor: '#ff2a74',
                    backgroundColor: 'rgba(255, 42, 116, 0.05)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'yRevenue'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#f5f6fa',
                        font: { family: 'Outfit', size: 12, weight: 600 }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8b94a0', font: { family: 'Outfit' } }
                },
                yQty: {
                    type: 'linear',
                    position: 'left',
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#00f0ff', font: { family: 'Outfit' } },
                    title: { display: true, text: 'Quantity (Units)', color: '#00f0ff', font: { family: 'Outfit', weight: 600 } }
                },
                yRevenue: {
                    type: 'linear',
                    position: 'right',
                    grid: { drawOnChartArea: false }, // avoid duplicate gridlines
                    ticks: { color: '#ff2a74', font: { family: 'Outfit' } },
                    title: { display: true, text: 'Revenue ($)', color: '#ff2a74', font: { family: 'Outfit', weight: 600 } }
                }
            }
        }
    });
}

// Render Forecast vs Actual Bar Chart (Side by Side)
function renderForecastActualChart(compareData) {
    const ctx = document.getElementById('forecastActualChart');
    if (!ctx) return;

    if (forecastActualChartInst) {
        forecastActualChartInst.destroy();
    }

    const labels = compareData.map(d => d.date);
    const actuals = compareData.map(d => d.actual);
    const forecasts = compareData.map(d => d.forecast);

    forecastActualChartInst = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Predicted Demand (Baked)',
                    data: forecasts,
                    backgroundColor: 'rgba(255, 42, 116, 0.65)',
                    borderColor: '#ff2a74',
                    borderWidth: 1.5,
                    borderRadius: 4
                },
                {
                    label: 'Actual Units Sold',
                    data: actuals,
                    backgroundColor: 'rgba(0, 240, 255, 0.65)',
                    borderColor: '#00f0ff',
                    borderWidth: 1.5,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#f5f6fa',
                        font: { family: 'Outfit', size: 12, weight: 600 }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8b94a0', font: { family: 'Outfit' } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#f5f6fa', font: { family: 'Outfit' } },
                    title: { display: true, text: 'Bake / Sales Volume', color: '#f5f6fa', font: { family: 'Outfit', weight: 600 } }
                }
            }
        }
    });
}

// Chatbot UI Toggle
function toggleChat() {
    const chatWindow = document.getElementById('chatbot-window');
    if (chatWindow) {
        chatWindow.classList.toggle('active');
        if (chatWindow.classList.contains('active')) {
            const input = document.getElementById('chatbot-input');
            if (input) input.focus();
            scrollChatToBottom();
        }
    }
}

// Scroll chat container
function scrollChatToBottom() {
    const messagesDiv = document.getElementById('chatbot-messages');
    if (messagesDiv) {
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

// Simple Markdown Formatter for Chat Bubble HTML
function formatMarkdown(text) {
    // Bold: **text** -> <strong>text</strong>
    let html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Bullet points: * text or - text -> <li>text</li>
    const lines = html.split('\n');
    let inList = false;
    const parsedLines = lines.map(line => {
        const trimmed = line.trim();
        if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
            const content = trimmed.substring(2);
            let result = '';
            if (!inList) {
                result += '<ul style="margin-left: 1.25rem; margin-top: 0.5rem; margin-bottom: 0.5rem; list-style-type: disc;">';
                inList = true;
            }
            result += `<li style="margin-bottom: 0.25rem;">${content}</li>`;
            return result;
        } else {
            let result = '';
            if (inList) {
                result += '</ul>';
                inList = false;
            }
            result += line;
            return result;
        }
    });
    if (inList) {
        parsedLines.push('</ul>');
    }
    return parsedLines.join('<br>');
}

// Send chat message
async function sendChatMessage() {
    const input = document.getElementById('chatbot-input');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';

    const messagesDiv = document.getElementById('chatbot-messages');
    
    // Add user message
    const userBubble = document.createElement('div');
    userBubble.className = 'msg user-msg';
    userBubble.innerHTML = `<p>${message}</p>`;
    messagesDiv.appendChild(userBubble);
    scrollChatToBottom();

    // Add typing indicator
    const typingBubble = document.createElement('div');
    typingBubble.className = 'msg bot-msg typing-bubble';
    typingBubble.id = 'typing-indicator';
    typingBubble.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    messagesDiv.appendChild(typingBubble);
    scrollChatToBottom();

    try {
        const response = await fetch('/api/ai_chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();

        const botBubble = document.createElement('div');
        botBubble.className = 'msg bot-msg';
        
        if (response.ok) {
            botBubble.innerHTML = `<p>${formatMarkdown(data.response)}</p>`;
        } else {
            botBubble.innerHTML = `<p style="color: var(--color-danger);"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${data.error || "Failed to get reply."}</p>`;
        }
        
        messagesDiv.appendChild(botBubble);
    } catch (err) {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();

        const errorBubble = document.createElement('div');
        errorBubble.className = 'msg bot-msg';
        errorBubble.innerHTML = `<p style="color: var(--color-danger);"><i class="fa-solid fa-triangle-exclamation"></i> Error: Failed to connect to server.</p>`;
        messagesDiv.appendChild(errorBubble);
    }
    
    scrollChatToBottom();
}
