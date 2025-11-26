"""
Flask Web Application for Sharpe Ratio Optimizer
Professional frontend for portfolio optimization and backtesting
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
import io
import base64

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from utils import download_data, calculate_log_returns, get_performance_metrics
from optimizer import SharpeOptimizer
from backtest import Backtester
from rolling_optimizer import RollingOptimizer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Enable CORS for Vercel frontend
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "https://*.vercel.app"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Global configuration
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/optimize', methods=['POST'])
def optimize_portfolio():
    """Run portfolio optimization"""
    try:
        data = request.json
        symbols = [s.strip().upper() for s in data.get('symbols', 'SPY,GLD,AGG').split(',')]
        start_date = data.get('start_date', '2015-01-01')
        end_date = data.get('end_date', '2024-12-31')
        risk_free_rate = float(data.get('risk_free_rate', 0.02))
        n_portfolios = int(data.get('n_portfolios', 5000))
        
        # Download data
        prices = download_data(symbols, start_date, end_date)
        returns = calculate_log_returns(prices)
        
        # Initialize optimizer
        optimizer = SharpeOptimizer(returns, risk_free_rate=risk_free_rate)
        
        # Calculate analytical tangency portfolio
        analytical_weights, analytical_metrics = optimizer.analytical_tangency_portfolio()
        
        # Calculate constrained optimal portfolio
        constrained_weights, constrained_metrics = optimizer.constrained_optimization()
        
        # Generate efficient frontier
        frontier_df = optimizer.generate_efficient_frontier(n_portfolios=n_portfolios)
        
        # Prepare response
        response = {
            'success': True,
            'symbols': symbols,
            'analytical': {
                'weights': dict(zip(symbols, analytical_weights.tolist())),
                'return': float(analytical_metrics['return']),
                'volatility': float(analytical_metrics['volatility']),
                'sharpe': float(analytical_metrics['sharpe'])
            },
            'constrained': {
                'weights': dict(zip(symbols, constrained_weights.tolist())),
                'return': float(constrained_metrics['return']),
                'volatility': float(constrained_metrics['volatility']),
                'sharpe': float(constrained_metrics['sharpe'])
            },
            'frontier': {
                'returns': frontier_df['return'].tolist(),
                'volatilities': frontier_df['volatility'].tolist(),
                'sharpes': frontier_df['sharpe'].tolist()
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """Run static backtest"""
    try:
        data = request.json
        symbols = [s.strip().upper() for s in data.get('symbols', 'SPY,GLD,AGG').split(',')]
        start_date = data.get('start_date', '2015-01-01')
        end_date = data.get('end_date', '2024-12-31')
        risk_free_rate = float(data.get('risk_free_rate', 0.02))
        cost_bps = float(data.get('cost_bps', 10.0))
        use_constrained = data.get('use_constrained', True)
        
        # Download data
        prices = download_data(symbols, start_date, end_date)
        returns = calculate_log_returns(prices)
        
        # Get optimal weights
        optimizer = SharpeOptimizer(returns, risk_free_rate=risk_free_rate)
        
        if use_constrained:
            weights, _ = optimizer.constrained_optimization()
        else:
            weights, _ = optimizer.analytical_tangency_portfolio()
        
        # Run backtest
        backtester = Backtester(prices, weights, symbols, transaction_cost_bps=cost_bps)
        results, metrics = backtester.run_static_backtest()
        
        # Prepare response
        response = {
            'success': True,
            'weights': dict(zip(symbols, weights.tolist())),
            'metrics': {
                'annual_return': float(metrics['Annual Return']),
                'annual_volatility': float(metrics['Annual Volatility']),
                'sharpe_ratio': float(metrics['Sharpe Ratio']),
                'max_drawdown': float(metrics['Max Drawdown']),
                'cumulative_return': float(metrics['Cumulative Return'])
            },
            'equity_curve': {
                'dates': results['date'].dt.strftime('%Y-%m-%d').tolist(),
                'values': results['cumulative_return'].tolist()
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/rolling_backtest', methods=['POST'])
def run_rolling_backtest():
    """Run rolling window backtest"""
    try:
        data = request.json
        symbols = [s.strip().upper() for s in data.get('symbols', 'SPY,GLD,AGG').split(',')]
        start_date = data.get('start_date', '2012-01-01')
        end_date = data.get('end_date', '2024-12-31')
        risk_free_rate = float(data.get('risk_free_rate', 0.02))
        lookback_months = int(data.get('lookback_months', 36))
        cost_bps = float(data.get('cost_bps', 10.0))
        
        # Download data
        prices = download_data(symbols, start_date, end_date)
        
        # Initialize rolling optimizer
        rolling_opt = RollingOptimizer(
            prices=prices,
            symbols=symbols,
            lookback_months=lookback_months,
            risk_free_rate=risk_free_rate,
            transaction_cost_bps=cost_bps,
            use_constrained=True
        )
        
        # Run rolling backtest
        results_df, weights_df, metrics = rolling_opt.run_rolling_backtest()
        
        # Prepare weights history
        weight_cols = [col for col in weights_df.columns if col.endswith('_weight')]
        weights_history = {}
        for col in weight_cols:
            symbol = col.replace('_weight', '')
            weights_history[symbol] = weights_df[col].tolist()
        
        # Prepare response
        response = {
            'success': True,
            'metrics': {
                'annual_return': float(metrics['Annual Return']),
                'annual_volatility': float(metrics['Annual Volatility']),
                'sharpe_ratio': float(metrics['Sharpe Ratio']),
                'max_drawdown': float(metrics['Max Drawdown']),
                'cumulative_return': float(metrics['Cumulative Return']),
                'num_rebalances': int(metrics['Number of Rebalances']),
                'avg_turnover': float(metrics['Average Turnover']),
                'total_costs': float(metrics['Total Transaction Costs'])
            },
            'equity_curve': {
                'dates': results_df['date'].dt.strftime('%Y-%m-%d').tolist(),
                'values': results_df['cumulative_return'].tolist()
            },
            'weights_history': {
                'dates': weights_df['date'].dt.strftime('%Y-%m-%d').tolist(),
                'weights': weights_history
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/results')
def get_results():
    """Get list of saved results"""
    try:
        files = {
            'frontier': os.path.exists(os.path.join(OUTPUT_DIR, 'frontier.png')),
            'equity_curve': os.path.exists(os.path.join(OUTPUT_DIR, 'equity_curve.png')),
            'rolling_backtest': os.path.exists(os.path.join(OUTPUT_DIR, 'rolling_backtest.png')),
            'optimal_weights': os.path.exists(os.path.join(OUTPUT_DIR, 'optimal_weights.csv')),
            'backtest_metrics': os.path.exists(os.path.join(OUTPUT_DIR, 'backtest_metrics.csv')),
            'rolling_metrics': os.path.exists(os.path.join(OUTPUT_DIR, 'rolling_metrics.csv'))
        }
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


if __name__ == '__main__':
    print("=" * 60)
    print("SHARPE RATIO OPTIMIZER - WEB INTERFACE")
    print("=" * 60)
    print("\nStarting Flask server...")
    print("Open your browser and navigate to: http://localhost:5000")
    print("\nPress CTRL+C to stop the server")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
