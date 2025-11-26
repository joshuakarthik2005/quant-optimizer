"""
Backtesting module for portfolio strategies.

This module implements:
1. Static portfolio backtesting
2. Performance metrics calculation
3. Transaction cost modeling
4. Equity curve generation
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.utils import (
    download_data, calculate_log_returns, get_performance_metrics,
    calculate_max_drawdown
)
from scripts.optimizer import SharpeOptimizer


class Backtester:
    """
    Portfolio backtesting engine.
    
    Supports static portfolio backtesting with transaction costs.
    """
    
    def __init__(self, prices: pd.DataFrame, weights: np.ndarray, 
                 symbols: list, transaction_cost_bps: float = 10.0):
        """
        Initialize backtester.
        
        Parameters:
        -----------
        prices : pd.DataFrame
            Historical price data
        weights : np.ndarray
            Portfolio weights (must sum to 1)
        symbols : list
            List of asset symbols
        transaction_cost_bps : float
            Transaction cost in basis points (10 bps = 0.1%)
        """
        self.prices = prices
        self.weights = weights
        self.symbols = symbols
        self.transaction_cost_bps = transaction_cost_bps
        
        # Calculate returns
        self.returns = calculate_log_returns(prices)
        
        print(f"Initialized backtester")
        print(f"Period: {prices.index[0].date()} to {prices.index[-1].date()}")
        print(f"Assets: {symbols}")
        print(f"Transaction costs: {transaction_cost_bps} bps")
    
    def run_static_backtest(self) -> pd.DataFrame:
        """
        Run static portfolio backtest (buy and hold with rebalancing).
        
        Returns:
        --------
        pd.DataFrame
            DataFrame with date, portfolio_return, cumulative_return columns
        """
        print("\nRunning static backtest...")
        
        # Calculate portfolio returns: R_p = sum(w_i * r_i)
        portfolio_returns = (self.returns * self.weights).sum(axis=1)
        
        # Apply transaction costs (assume rebalancing at start)
        # Initial turnover = sum of absolute weights / 2 = 0.5 (going from cash to portfolio)
        initial_turnover = 0.5
        initial_cost = initial_turnover * (self.transaction_cost_bps / 10000)
        
        # Subtract initial cost from first return
        portfolio_returns.iloc[0] -= initial_cost
        
        # Calculate cumulative returns
        cumulative_returns = (1 + portfolio_returns).cumprod()
        
        # Create results DataFrame
        results = pd.DataFrame({
            'date': portfolio_returns.index,
            'portfolio_return': portfolio_returns.values,
            'cumulative_return': cumulative_returns.values
        })
        
        # Calculate performance metrics
        metrics = get_performance_metrics(portfolio_returns, periods_per_year=252)
        
        print("\n=== Backtest Performance Metrics ===")
        print(f"Annual Return: {metrics['Annual Return']:.2%}")
        print(f"Annual Volatility: {metrics['Annual Volatility']:.2%}")
        print(f"Sharpe Ratio: {metrics['Sharpe Ratio']:.4f}")
        print(f"Max Drawdown: {metrics['Max Drawdown']:.2%}")
        print(f"Cumulative Return: {metrics['Cumulative Return']:.2%}")
        print(f"Total Days: {metrics['Total Days']}")
        
        return results, metrics
    
    def plot_equity_curve(self, results: pd.DataFrame, save_path: str = None):
        """
        Plot equity curve.
        
        Parameters:
        -----------
        results : pd.DataFrame
            Backtest results with cumulative returns
        save_path : str
            Path to save plot (if None, displays plot)
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot cumulative returns
        ax1.plot(results['date'], results['cumulative_return'], 
                linewidth=2, color='darkblue', label='Portfolio')
        ax1.axhline(y=1, color='black', linestyle='--', alpha=0.3)
        ax1.set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Cumulative Return (Starting at $1)', fontsize=12)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # Plot drawdown
        cumulative = results['cumulative_return']
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        
        ax2.fill_between(results['date'], drawdown, 0, 
                         color='red', alpha=0.3, label='Drawdown')
        ax2.set_title('Portfolio Drawdown', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Drawdown', fontsize=12)
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        
        # Format y-axis as percentage
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'{y*100:.1f}%'))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"\nEquity curve saved to {save_path}")
        else:
            plt.show()
        
        plt.close()


def main():
    """Main execution function with CLI support."""
    parser = argparse.ArgumentParser(description='Portfolio Backtester')
    parser.add_argument('--symbols', type=str, default='SPY,GLD,AGG',
                       help='Comma-separated list of ticker symbols')
    parser.add_argument('--start', type=str, default='2015-01-01',
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-12-31',
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--rf', type=float, default=0.02,
                       help='Risk-free rate (decimal)')
    parser.add_argument('--cost_bps', type=float, default=10.0,
                       help='Transaction cost in basis points (10 bps = 0.1 percent)')
    parser.add_argument('--use_constrained', action='store_true',
                       help='Use constrained optimal weights instead of analytical')
    
    args = parser.parse_args()
    
    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    print("=" * 60)
    print("PORTFOLIO BACKTESTER")
    print("=" * 60)
    
    # Download data
    prices = download_data(symbols, args.start, args.end)
    
    # Calculate returns for optimization
    returns = calculate_log_returns(prices)
    
    # Get optimal weights
    optimizer = SharpeOptimizer(returns, risk_free_rate=args.rf)
    
    if args.use_constrained:
        weights, _ = optimizer.constrained_optimization()
        method = "Constrained"
    else:
        weights, _ = optimizer.analytical_tangency_portfolio()
        method = "Analytical"
    
    print(f"\nUsing {method} optimal weights for backtesting")
    
    # Run backtest
    backtester = Backtester(prices, weights, symbols, 
                           transaction_cost_bps=args.cost_bps)
    results, metrics = backtester.run_static_backtest()
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    
    # Save results
    results_path = os.path.join(output_dir, 'backtest_results.csv')
    results.to_csv(results_path, index=False)
    print(f"\nResults saved to {results_path}")
    
    # Save metrics
    metrics_df = pd.DataFrame([metrics])
    metrics_path = os.path.join(output_dir, 'backtest_metrics.csv')
    metrics_df.to_csv(metrics_path, index=False)
    print(f"Metrics saved to {metrics_path}")
    
    # Plot equity curve
    plot_path = os.path.join(output_dir, 'equity_curve.png')
    backtester.plot_equity_curve(results, save_path=plot_path)
    
    print("\n" + "=" * 60)
    print("BACKTEST COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
