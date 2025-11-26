"""
Rolling window portfolio optimization and backtesting.

This module implements:
1. Rolling window optimization (monthly rebalancing)
2. Out-of-sample backtesting
3. Transaction cost accounting
4. Performance tracking over time
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from dateutil.relativedelta import relativedelta
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.utils import (
    download_data, calculate_log_returns, get_performance_metrics,
    calculate_turnover
)
from scripts.optimizer import SharpeOptimizer


class RollingOptimizer:
    """
    Rolling window portfolio optimizer with monthly rebalancing.
    
    Uses a lookback window to optimize weights, then applies them
    to the next period. Rebalances monthly.
    """
    
    def __init__(self, prices: pd.DataFrame, symbols: list,
                 lookback_months: int = 36, risk_free_rate: float = 0.02,
                 transaction_cost_bps: float = 10.0, use_constrained: bool = True):
        """
        Initialize rolling optimizer.
        
        Parameters:
        -----------
        prices : pd.DataFrame
            Historical price data
        symbols : list
            List of asset symbols
        lookback_months : int
            Lookback window in months (default: 36 = 3 years)
        risk_free_rate : float
            Annual risk-free rate
        transaction_cost_bps : float
            Transaction cost in basis points
        use_constrained : bool
            If True, use constrained optimization; else use analytical
        """
        self.prices = prices
        self.symbols = symbols
        self.lookback_months = lookback_months
        self.risk_free_rate = risk_free_rate
        self.transaction_cost_bps = transaction_cost_bps
        self.use_constrained = use_constrained
        self.n_assets = len(symbols)
        
        print(f"Initialized rolling optimizer")
        print(f"Lookback window: {lookback_months} months")
        print(f"Risk-free rate: {risk_free_rate:.2%}")
        print(f"Transaction costs: {transaction_cost_bps} bps")
        print(f"Optimization method: {'Constrained' if use_constrained else 'Analytical'}")
    
    def get_rebalance_dates(self) -> list:
        """
        Generate monthly rebalancing dates.
        
        Returns:
        --------
        list
            List of rebalancing dates
        """
        dates = self.prices.index
        
        # Get first day of each month
        monthly_dates = dates.to_series().groupby([dates.year, dates.month]).first()
        
        # Need enough history for first optimization
        first_valid_date = dates[0] + relativedelta(months=self.lookback_months)
        
        rebalance_dates = [d for d in monthly_dates if d >= first_valid_date]
        
        print(f"\nGenerated {len(rebalance_dates)} rebalancing dates")
        print(f"First rebalance: {rebalance_dates[0].date()}")
        print(f"Last rebalance: {rebalance_dates[-1].date()}")
        
        return rebalance_dates
    
    def optimize_at_date(self, date: datetime) -> np.ndarray:
        """
        Optimize portfolio weights using data up to given date.
        
        Parameters:
        -----------
        date : datetime
            Optimization date
        
        Returns:
        --------
        np.ndarray
            Optimal portfolio weights
        """
        # Get lookback window
        end_date = date
        start_date = date - relativedelta(months=self.lookback_months)
        
        # Filter prices
        mask = (self.prices.index >= start_date) & (self.prices.index <= end_date)
        prices_window = self.prices[mask]
        
        if len(prices_window) < 20:  # Need minimum data
            print(f"Warning: Insufficient data at {date.date()}, using equal weights")
            return np.ones(self.n_assets) / self.n_assets
        
        # Calculate returns
        returns_window = calculate_log_returns(prices_window)
        
        # Optimize
        optimizer = SharpeOptimizer(returns_window, risk_free_rate=self.risk_free_rate)
        
        if self.use_constrained:
            weights, _ = optimizer.constrained_optimization()
        else:
            weights, _ = optimizer.analytical_tangency_portfolio()
        
        return weights
    
    def run_rolling_backtest(self) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
        """
        Run rolling window backtest with monthly rebalancing.
        
        Returns:
        --------
        results_df : pd.DataFrame
            Daily returns and cumulative performance
        weights_df : pd.DataFrame
            Weights at each rebalancing date
        metrics : dict
            Overall performance metrics
        """
        print("\n" + "=" * 60)
        print("RUNNING ROLLING WINDOW BACKTEST")
        print("=" * 60)
        
        # Get rebalancing dates
        rebalance_dates = self.get_rebalance_dates()
        
        # Calculate all returns
        all_returns = calculate_log_returns(self.prices)
        
        # Initialize tracking
        portfolio_returns = pd.Series(index=all_returns.index, dtype=float)
        weights_history = []
        current_weights = None
        previous_weights = np.zeros(self.n_assets)
        
        for i, rebal_date in enumerate(rebalance_dates):
            print(f"\nRebalancing {i+1}/{len(rebalance_dates)}: {rebal_date.date()}")
            
            # Optimize weights
            new_weights = self.optimize_at_date(rebal_date)
            
            print(f"Weights: {dict(zip(self.symbols, new_weights))}")
            
            # Calculate turnover and transaction costs
            turnover = calculate_turnover(previous_weights, new_weights)
            transaction_cost = turnover * (self.transaction_cost_bps / 10000)
            
            print(f"Turnover: {turnover:.4f}, Cost: {transaction_cost:.4f}")
            
            # Store weights
            weights_history.append({
                'date': rebal_date,
                **{f'{symbol}_weight': w for symbol, w in zip(self.symbols, new_weights)},
                'turnover': turnover,
                'transaction_cost': transaction_cost
            })
            
            # Determine holding period
            if i < len(rebalance_dates) - 1:
                next_rebal_date = rebalance_dates[i + 1]
            else:
                next_rebal_date = all_returns.index[-1]
            
            # Calculate portfolio returns for this period
            period_mask = (all_returns.index >= rebal_date) & (all_returns.index < next_rebal_date)
            period_returns = all_returns[period_mask]
            
            if len(period_returns) > 0:
                # Portfolio returns: R_p = sum(w_i * r_i)
                period_portfolio_returns = (period_returns * new_weights).sum(axis=1)
                
                # Apply transaction cost to first day of period
                period_portfolio_returns.iloc[0] -= transaction_cost
                
                # Store returns
                portfolio_returns[period_mask] = period_portfolio_returns
            
            previous_weights = new_weights.copy()
        
        # Remove any NaN values
        portfolio_returns = portfolio_returns.dropna()
        
        # Calculate cumulative returns
        cumulative_returns = (1 + portfolio_returns).cumprod()
        
        # Create results DataFrame
        results_df = pd.DataFrame({
            'date': portfolio_returns.index,
            'portfolio_return': portfolio_returns.values,
            'cumulative_return': cumulative_returns.values
        })
        
        # Create weights DataFrame
        weights_df = pd.DataFrame(weights_history)
        
        # Calculate performance metrics
        metrics = get_performance_metrics(portfolio_returns, periods_per_year=252)
        
        # Add rolling-specific metrics
        avg_turnover = weights_df['turnover'].mean()
        total_transaction_costs = weights_df['transaction_cost'].sum()
        
        metrics['Average Turnover'] = avg_turnover
        metrics['Total Transaction Costs'] = total_transaction_costs
        metrics['Number of Rebalances'] = len(rebalance_dates)
        
        print("\n" + "=" * 60)
        print("ROLLING BACKTEST PERFORMANCE METRICS")
        print("=" * 60)
        print(f"Annual Return: {metrics['Annual Return']:.2%}")
        print(f"Annual Volatility: {metrics['Annual Volatility']:.2%}")
        print(f"Sharpe Ratio: {metrics['Sharpe Ratio']:.4f}")
        print(f"Max Drawdown: {metrics['Max Drawdown']:.2%}")
        print(f"Cumulative Return: {metrics['Cumulative Return']:.2%}")
        print(f"Number of Rebalances: {metrics['Number of Rebalances']}")
        print(f"Average Turnover: {metrics['Average Turnover']:.2%}")
        print(f"Total Transaction Costs: {metrics['Total Transaction Costs']:.4f}")
        
        return results_df, weights_df, metrics
    
    def plot_rolling_results(self, results_df: pd.DataFrame, 
                            weights_df: pd.DataFrame,
                            save_path: str = None):
        """
        Plot rolling backtest results.
        
        Parameters:
        -----------
        results_df : pd.DataFrame
            Backtest results
        weights_df : pd.DataFrame
            Weights history
        save_path : str
            Path to save plot
        """
        fig, axes = plt.subplots(3, 1, figsize=(14, 12))
        
        # 1. Equity curve
        ax1 = axes[0]
        ax1.plot(results_df['date'], results_df['cumulative_return'],
                linewidth=2, color='darkblue', label='Portfolio')
        ax1.axhline(y=1, color='black', linestyle='--', alpha=0.3)
        ax1.set_title('Rolling Portfolio Equity Curve', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Cumulative Return', fontsize=12)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # 2. Drawdown
        ax2 = axes[1]
        cumulative = results_df['cumulative_return']
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        ax2.fill_between(results_df['date'], drawdown, 0,
                         color='red', alpha=0.3, label='Drawdown')
        ax2.set_title('Portfolio Drawdown', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Drawdown', fontsize=12)
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'{y*100:.1f}%'))
        
        # 3. Weights over time
        ax3 = axes[2]
        weight_cols = [col for col in weights_df.columns if col.endswith('_weight')]
        for col in weight_cols:
            symbol = col.replace('_weight', '')
            ax3.plot(weights_df['date'], weights_df[col], 
                    linewidth=2, marker='o', markersize=4, label=symbol)
        ax3.set_title('Portfolio Weights Over Time', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Date', fontsize=12)
        ax3.set_ylabel('Weight', fontsize=12)
        ax3.legend(loc='best')
        ax3.grid(True, alpha=0.3)
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'{y*100:.0f}%'))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"\nPlot saved to {save_path}")
        else:
            plt.show()
        
        plt.close()


def main():
    """Main execution function with CLI support."""
    parser = argparse.ArgumentParser(description='Rolling Window Portfolio Optimizer')
    parser.add_argument('--symbols', type=str, default='SPY,GLD,AGG',
                       help='Comma-separated list of ticker symbols')
    parser.add_argument('--start', type=str, default='2012-01-01',
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-12-31',
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--lookback', type=int, default=36,
                       help='Lookback window in months')
    parser.add_argument('--rf', type=float, default=0.02,
                       help='Risk-free rate (decimal)')
    parser.add_argument('--cost_bps', type=float, default=10.0,
                       help='Transaction cost in basis points (10 bps = 0.1 percent)')
    parser.add_argument('--use_analytical', action='store_true',
                       help='Use analytical weights instead of constrained')
    
    args = parser.parse_args()
    
    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    print("=" * 60)
    print("ROLLING WINDOW PORTFOLIO OPTIMIZER")
    print("=" * 60)
    
    # Download data
    prices = download_data(symbols, args.start, args.end)
    
    # Initialize rolling optimizer
    rolling_opt = RollingOptimizer(
        prices=prices,
        symbols=symbols,
        lookback_months=args.lookback,
        risk_free_rate=args.rf,
        transaction_cost_bps=args.cost_bps,
        use_constrained=not args.use_analytical
    )
    
    # Run rolling backtest
    results_df, weights_df, metrics = rolling_opt.run_rolling_backtest()
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    
    # Save results
    results_path = os.path.join(output_dir, 'rolling_backtest_results.csv')
    results_df.to_csv(results_path, index=False)
    print(f"\nResults saved to {results_path}")
    
    # Save weights
    weights_path = os.path.join(output_dir, 'rolling_weights.csv')
    weights_df.to_csv(weights_path, index=False)
    print(f"Weights saved to {weights_path}")
    
    # Save metrics
    metrics_df = pd.DataFrame([metrics])
    metrics_path = os.path.join(output_dir, 'rolling_metrics.csv')
    metrics_df.to_csv(metrics_path, index=False)
    print(f"Metrics saved to {metrics_path}")
    
    # Plot results
    plot_path = os.path.join(output_dir, 'rolling_backtest.png')
    rolling_opt.plot_rolling_results(results_df, weights_df, save_path=plot_path)
    
    print("\n" + "=" * 60)
    print("ROLLING BACKTEST COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
