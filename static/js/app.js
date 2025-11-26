// API Configuration
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:5000' 
    : 'https://your-app.onrender.com'; // Replace with your Render URL after deployment

// Tab Navigation
const navBtns = document.querySelectorAll('.nav-btn');
const tabContents = document.querySelectorAll('.tab-content');

navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.dataset.tab;
        
        // Remove active class from all
        navBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(t => t.classList.remove('active'));
        
        // Add active class to clicked
        btn.classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');
    });
});

// Utility Functions
function showLoading(buttonId) {
    const btn = document.getElementById(buttonId);
    btn.classList.add('loading');
    btn.disabled = true;
}

function hideLoading(buttonId) {
    const btn = document.getElementById(buttonId);
    btn.classList.remove('loading');
    btn.disabled = false;
}

function formatPercent(value) {
    return (value * 100).toFixed(2) + '%';
}

function formatNumber(value, decimals = 4) {
    return value.toFixed(decimals);
}

function showWeights(containerId, weights) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    const sortedWeights = Object.entries(weights).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
    
    sortedWeights.forEach(([symbol, weight]) => {
        const weightPercent = Math.abs(weight * 100);
        const isNegative = weight < 0;
        
        const weightBar = document.createElement('div');
        weightBar.className = 'weight-bar';
        weightBar.innerHTML = `
            <div class="weight-label">${symbol}</div>
            <div class="weight-track">
                <div class="weight-fill" style="width: ${Math.min(weightPercent, 100)}%; ${isNegative ? 'background: #ef4444;' : ''}">
                    ${formatPercent(weight)}
                </div>
            </div>
        `;
        container.appendChild(weightBar);
    });
}

// Portfolio Optimizer
document.getElementById('optimize-btn').addEventListener('click', async () => {
    showLoading('optimize-btn');
    
    const data = {
        symbols: document.getElementById('opt-symbols').value,
        start_date: document.getElementById('opt-start').value,
        end_date: document.getElementById('opt-end').value,
        risk_free_rate: parseFloat(document.getElementById('opt-rf').value),
        n_portfolios: parseInt(document.getElementById('opt-portfolios').value)
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/optimize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Display constrained results
            document.getElementById('opt-const-return').textContent = formatPercent(result.constrained.return);
            document.getElementById('opt-const-vol').textContent = formatPercent(result.constrained.volatility);
            document.getElementById('opt-const-sharpe').textContent = formatNumber(result.constrained.sharpe);
            showWeights('opt-const-weights', result.constrained.weights);
            
            // Display analytical results
            document.getElementById('opt-anal-return').textContent = formatPercent(result.analytical.return);
            document.getElementById('opt-anal-vol').textContent = formatPercent(result.analytical.volatility);
            document.getElementById('opt-anal-sharpe').textContent = formatNumber(result.analytical.sharpe);
            showWeights('opt-anal-weights', result.analytical.weights);
            
            // Plot efficient frontier
            plotEfficientFrontier(result.frontier, result.constrained, result.analytical);
            
            document.getElementById('opt-results').style.display = 'block';
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        hideLoading('optimize-btn');
    }
});

// Static Backtest
document.getElementById('backtest-btn').addEventListener('click', async () => {
    showLoading('backtest-btn');
    
    const data = {
        symbols: document.getElementById('bt-symbols').value,
        start_date: document.getElementById('bt-start').value,
        end_date: document.getElementById('bt-end').value,
        risk_free_rate: parseFloat(document.getElementById('bt-rf').value),
        cost_bps: parseFloat(document.getElementById('bt-cost').value),
        use_constrained: true
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/backtest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Display metrics
            document.getElementById('bt-return').textContent = formatPercent(result.metrics.annual_return);
            document.getElementById('bt-vol').textContent = formatPercent(result.metrics.annual_volatility);
            document.getElementById('bt-sharpe').textContent = formatNumber(result.metrics.sharpe_ratio);
            document.getElementById('bt-dd').textContent = formatPercent(result.metrics.max_drawdown);
            document.getElementById('bt-cumret').textContent = formatPercent(result.metrics.cumulative_return);
            
            // Display weights
            showWeights('bt-weights', result.weights);
            
            // Plot equity curve
            plotEquityCurve('backtest-chart', result.equity_curve);
            
            document.getElementById('bt-results').style.display = 'block';
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        hideLoading('backtest-btn');
    }
});

// Rolling Backtest
document.getElementById('rolling-btn').addEventListener('click', async () => {
    showLoading('rolling-btn');
    
    const data = {
        symbols: document.getElementById('roll-symbols').value,
        start_date: document.getElementById('roll-start').value,
        end_date: document.getElementById('roll-end').value,
        risk_free_rate: parseFloat(document.getElementById('roll-rf').value),
        lookback_months: parseInt(document.getElementById('roll-lookback').value),
        cost_bps: parseFloat(document.getElementById('roll-cost').value)
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/rolling_backtest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Display metrics
            document.getElementById('roll-return').textContent = formatPercent(result.metrics.annual_return);
            document.getElementById('roll-sharpe').textContent = formatNumber(result.metrics.sharpe_ratio);
            document.getElementById('roll-dd').textContent = formatPercent(result.metrics.max_drawdown);
            document.getElementById('roll-rebal').textContent = result.metrics.num_rebalances;
            document.getElementById('roll-turn').textContent = formatPercent(result.metrics.avg_turnover);
            document.getElementById('roll-costs').textContent = formatPercent(result.metrics.total_costs);
            
            // Plot equity curve
            plotEquityCurve('rolling-equity-chart', result.equity_curve);
            
            // Plot weights evolution
            plotWeightsEvolution('rolling-weights-chart', result.weights_history);
            
            document.getElementById('roll-results').style.display = 'block';
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        hideLoading('rolling-btn');
    }
});

// Chart Functions
let frontierChart = null;
let backtestChart = null;
let rollingEquityChart = null;
let rollingWeightsChart = null;

function plotEfficientFrontier(frontier, constrained, analytical) {
    const ctx = document.getElementById('frontier-chart');
    
    if (frontierChart) {
        frontierChart.destroy();
    }
    
    frontierChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Random Portfolios',
                    data: frontier.volatilities.map((vol, i) => ({
                        x: vol * 100,
                        y: frontier.returns[i] * 100
                    })),
                    backgroundColor: frontier.sharpes.map(s => {
                        const intensity = Math.max(0, Math.min(1, (s + 0.5) / 2));
                        return `rgba(37, 99, 235, ${intensity * 0.6})`;
                    }),
                    pointRadius: 3,
                    pointHoverRadius: 5
                },
                {
                    label: 'Constrained Optimal',
                    data: [{
                        x: constrained.volatility * 100,
                        y: constrained.return * 100
                    }],
                    backgroundColor: '#f59e0b',
                    pointRadius: 10,
                    pointStyle: 'rectRot',
                    pointBorderColor: '#000',
                    pointBorderWidth: 2
                },
                {
                    label: 'Analytical Tangency',
                    data: [{
                        x: analytical.volatility * 100,
                        y: analytical.return * 100
                    }],
                    backgroundColor: '#ef4444',
                    pointRadius: 12,
                    pointStyle: 'cross',
                    pointBorderColor: '#000',
                    pointBorderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Return: ${context.parsed.y.toFixed(2)}%, Vol: ${context.parsed.x.toFixed(2)}%`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Annual Volatility (%)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Annual Return (%)'
                    }
                }
            }
        }
    });
}

function plotEquityCurve(chartId, data) {
    const ctx = document.getElementById(chartId);
    
    const chart = chartId === 'backtest-chart' ? backtestChart : rollingEquityChart;
    
    if (chart) {
        chart.destroy();
    }
    
    const newChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [{
                label: 'Portfolio Value',
                data: data.values,
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.1,
                pointRadius: 0,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `Value: $${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    ticks: {
                        maxTicksLimit: 10
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Portfolio Value ($)'
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
    
    if (chartId === 'backtest-chart') {
        backtestChart = newChart;
    } else {
        rollingEquityChart = newChart;
    }
}

function plotWeightsEvolution(chartId, weightsHistory) {
    const ctx = document.getElementById(chartId);
    
    if (rollingWeightsChart) {
        rollingWeightsChart.destroy();
    }
    
    const colors = ['#2563eb', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'];
    const datasets = Object.entries(weightsHistory.weights).map(([symbol, weights], i) => ({
        label: symbol,
        data: weights.map(w => w * 100),
        borderColor: colors[i % colors.length],
        backgroundColor: colors[i % colors.length] + '40',
        borderWidth: 2,
        fill: false,
        tension: 0.1,
        pointRadius: 3,
        pointHoverRadius: 6
    }));
    
    rollingWeightsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: weightsHistory.dates,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    ticks: {
                        maxTicksLimit: 15
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Portfolio Weight (%)'
                    },
                    min: 0,
                    max: 100
                }
            }
        }
    });
}

// Set default dates
document.addEventListener('DOMContentLoaded', () => {
    const today = new Date().toISOString().split('T')[0];
    const tenYearsAgo = new Date(new Date().setFullYear(new Date().getFullYear() - 10)).toISOString().split('T')[0];
    const thirteenYearsAgo = new Date(new Date().setFullYear(new Date().getFullYear() - 13)).toISOString().split('T')[0];
    
    // Set default end dates to today
    document.getElementById('opt-end').value = today;
    document.getElementById('bt-end').value = today;
    document.getElementById('roll-end').value = today;
});
