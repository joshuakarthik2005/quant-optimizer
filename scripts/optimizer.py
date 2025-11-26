"""
Portfolio Optimization using Sharpe Ratio Maximization.

This module implements:
1. Analytical tangency portfolio calculation
2. Constrained Sharpe ratio optimization using SLSQP
3. Efficient frontier generation
4. Portfolio visualization
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.optimize import minimize
from typing import Tuple, List
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.utils import (
    download_data, calculate_log_returns, annualize_returns, 
    annualize_covariance, calculate_portfolio_return,
    calculate_portfolio_volatility, calculate_sharpe_ratio
)


class SharpeOptimizer:
    """
    Sharpe Ratio Optimizer for portfolio optimization.
    
    Implements both analytical and numerical optimization methods.
    """
    
    def __init__(self, returns: pd.DataFrame, risk_free_rate: float = 0.02):
        """
        Initialize optimizer with returns data.
        
        Parameters:
        -----------
        returns : pd.DataFrame
            DataFrame of asset returns
        risk_free_rate : float
            Annual risk-free rate (default: 2%)
        """
        self.returns = returns
        self.symbols = returns.columns.tolist()
        self.n_assets = len(self.symbols)
        self.risk_free_rate = risk_free_rate
        
        # Calculate mean returns and covariance (annualized)
        self.mean_returns = self.returns.mean() * 252
        self.cov_matrix = self.returns.cov() * 252
        
        print(f"Initialized optimizer with {self.n_assets} assets")
        print(f"Symbols: {self.symbols}")
        print(f"Risk-free rate: {self.risk_free_rate:.2%}")
    
    def analytical_tangency_portfolio(self) -> Tuple[np.ndarray, dict]:
        """
        Calculate analytical tangency portfolio.
        
        Formula: w* ∝ Σ^(-1) * (μ - r_f)
        Then normalize: w = w* / sum(w*)
        
        Returns:
        --------
        weights : np.ndarray
            Optimal portfolio weights
        metrics : dict
            Portfolio performance metrics
        """
        # Convert to numpy arrays
        mu = self.mean_returns.values
        Sigma = self.cov_matrix.values
        rf = self.risk_free_rate
        
        # Calculate inverse of covariance matrix
        try:
            Sigma_inv = np.linalg.inv(Sigma)
        except np.linalg.LinAlgError:
            print("Warning: Covariance matrix is singular, using pseudo-inverse")
            Sigma_inv = np.linalg.pinv(Sigma)
        
        # Calculate unnormalized weights: w* ∝ Σ^(-1) * (μ - r_f)
        ones = np.ones(self.n_assets)
        excess_returns = mu - rf * ones
        weights_unnormalized = Sigma_inv @ excess_returns
        
        # Normalize weights to sum to 1
        weights = weights_unnormalized / np.sum(weights_unnormalized)
        
        # Calculate portfolio metrics
        port_return = calculate_portfolio_return(weights, mu)
        port_vol = calculate_portfolio_volatility(weights, Sigma)
        sharpe = calculate_sharpe_ratio(weights, mu, Sigma, rf)
        
        metrics = {
            'return': port_return,
            'volatility': port_vol,
            'sharpe': sharpe
        }
        
        print("\n=== Analytical Tangency Portfolio ===")
        print(f"Expected Return: {port_return:.2%}")
        print(f"Volatility: {port_vol:.2%}")
        print(f"Sharpe Ratio: {sharpe:.4f}")
        print("\nWeights:")
        for symbol, weight in zip(self.symbols, weights):
            print(f"  {symbol}: {weight:.4f} ({weight*100:.2f}%)")
        
        return weights, metrics
    
    def constrained_optimization(self) -> Tuple[np.ndarray, dict]:
        """
        Optimize portfolio using constrained optimization (SLSQP).
        
        Constraints:
        - sum(w) = 1
        - 0 <= w_i <= 1 for all i
        
        Objective: Maximize Sharpe ratio (minimize negative Sharpe)
        
        Returns:
        --------
        weights : np.ndarray
            Optimal portfolio weights
        metrics : dict
            Portfolio performance metrics
        """
        mu = self.mean_returns.values
        Sigma = self.cov_matrix.values
        rf = self.risk_free_rate
        
        # Objective function: negative Sharpe ratio
        def negative_sharpe(w):
            return -calculate_sharpe_ratio(w, mu, Sigma, rf)
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}  # weights sum to 1
        ]
        
        # Bounds: 0 <= w_i <= 1
        bounds = tuple((0, 1) for _ in range(self.n_assets))
        
        # Initial guess: equal weights
        w0 = np.ones(self.n_assets) / self.n_assets
        
        # Optimize
        result = minimize(
            negative_sharpe,
            w0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if not result.success:
            print(f"Warning: Optimization did not converge: {result.message}")
        
        weights = result.x
        
        # Calculate portfolio metrics
        port_return = calculate_portfolio_return(weights, mu)
        port_vol = calculate_portfolio_volatility(weights, Sigma)
        sharpe = calculate_sharpe_ratio(weights, mu, Sigma, rf)
        
        metrics = {
            'return': port_return,
            'volatility': port_vol,
            'sharpe': sharpe
        }
        
        print("\n=== Constrained Optimal Portfolio ===")
        print(f"Expected Return: {port_return:.2%}")
        print(f"Volatility: {port_vol:.2%}")
        print(f"Sharpe Ratio: {sharpe:.4f}")
        print("\nWeights:")
        for symbol, weight in zip(self.symbols, weights):
            print(f"  {symbol}: {weight:.4f} ({weight*100:.2f}%)")
        
        return weights, metrics
    
    def generate_efficient_frontier(self, n_portfolios: int = 5000) -> pd.DataFrame:
        """
        Generate efficient frontier using random portfolio sampling.
        
        Parameters:
        -----------
        n_portfolios : int
            Number of random portfolios to generate
        
        Returns:
        --------
        pd.DataFrame
            DataFrame with columns: return, volatility, sharpe, weights
        """
        print(f"\nGenerating {n_portfolios} random portfolios...")
        
        mu = self.mean_returns.values
        Sigma = self.cov_matrix.values
        rf = self.risk_free_rate
        
        results = []
        
        for _ in range(n_portfolios):
            # Generate random weights that sum to 1
            weights = np.random.random(self.n_assets)
            weights /= np.sum(weights)
            
            # Calculate metrics
            port_return = calculate_portfolio_return(weights, mu)
            port_vol = calculate_portfolio_volatility(weights, Sigma)
            sharpe = calculate_sharpe_ratio(weights, mu, Sigma, rf)
            
            results.append({
                'return': port_return,
                'volatility': port_vol,
                'sharpe': sharpe,
                'weights': weights
            })
        
        df = pd.DataFrame(results)
        print(f"Generated {len(df)} portfolios")
        print(f"Return range: [{df['return'].min():.2%}, {df['return'].max():.2%}]")
        print(f"Volatility range: [{df['volatility'].min():.2%}, {df['volatility'].max():.2%}]")
        print(f"Sharpe range: [{df['sharpe'].min():.4f}, {df['sharpe'].max():.4f}]")
        
        return df
    
    def plot_efficient_frontier(self, frontier_df: pd.DataFrame, 
                               analytical_weights: np.ndarray,
                               constrained_weights: np.ndarray,
                               save_path: str = None):
        """
        Plot efficient frontier with optimal portfolios highlighted.
        
        Parameters:
        -----------
        frontier_df : pd.DataFrame
            DataFrame with frontier portfolios
        analytical_weights : np.ndarray
            Analytical tangency portfolio weights
        constrained_weights : np.ndarray
            Constrained optimal portfolio weights
        save_path : str
            Path to save the plot (if None, displays plot)
        """
        mu = self.mean_returns.values
        Sigma = self.cov_matrix.values
        rf = self.risk_free_rate
        
        # Calculate metrics for special portfolios
        analytical_ret = calculate_portfolio_return(analytical_weights, mu)
        analytical_vol = calculate_portfolio_volatility(analytical_weights, Sigma)
        analytical_sharpe = calculate_sharpe_ratio(analytical_weights, mu, Sigma, rf)
        
        constrained_ret = calculate_portfolio_return(constrained_weights, mu)
        constrained_vol = calculate_portfolio_volatility(constrained_weights, Sigma)
        constrained_sharpe = calculate_sharpe_ratio(constrained_weights, mu, Sigma, rf)
        
        # Best random portfolio
        best_idx = frontier_df['sharpe'].idxmax()
        best_ret = frontier_df.loc[best_idx, 'return']
        best_vol = frontier_df.loc[best_idx, 'volatility']
        best_sharpe = frontier_df.loc[best_idx, 'sharpe']
        
        # Create plot
        plt.figure(figsize=(12, 8))
        
        # Scatter plot colored by Sharpe ratio
        scatter = plt.scatter(
            frontier_df['volatility'], 
            frontier_df['return'],
            c=frontier_df['sharpe'],
            cmap='viridis',
            alpha=0.5,
            s=10,
            label='Random Portfolios'
        )
        plt.colorbar(scatter, label='Sharpe Ratio')
        
        # Plot analytical tangency portfolio
        plt.scatter(
            analytical_vol, analytical_ret,
            color='red', marker='X', s=500, 
            edgecolors='black', linewidths=2,
            label=f'Analytical Tangency (SR={analytical_sharpe:.3f})',
            zorder=5
        )
        
        # Plot constrained optimal portfolio
        plt.scatter(
            constrained_vol, constrained_ret,
            color='orange', marker='D', s=300,
            edgecolors='black', linewidths=2,
            label=f'Constrained Optimal (SR={constrained_sharpe:.3f})',
            zorder=5
        )
        
        # Plot best random portfolio
        plt.scatter(
            best_vol, best_ret,
            color='lime', marker='s', s=200,
            edgecolors='black', linewidths=2,
            label=f'Best Random (SR={best_sharpe:.3f})',
            zorder=5
        )
        
        # Labels and formatting
        plt.xlabel('Volatility (Annual)', fontsize=12)
        plt.ylabel('Expected Return (Annual)', fontsize=12)
        plt.title('Efficient Frontier - Sharpe Ratio Optimization', fontsize=14, fontweight='bold')
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3)
        
        # Format axes as percentages
        ax = plt.gca()
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x*100:.1f}%'))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'{y*100:.1f}%'))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"\nPlot saved to {save_path}")
        else:
            plt.show()
        
        plt.close()


def main():
    """Main execution function with CLI support."""
    parser = argparse.ArgumentParser(description='Sharpe Ratio Portfolio Optimizer')
    parser.add_argument('--symbols', type=str, default='SPY,GLD,AGG',
                       help='Comma-separated list of ticker symbols')
    parser.add_argument('--start', type=str, default='2015-01-01',
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-12-31',
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--rf', type=float, default=0.02,
                       help='Risk-free rate (decimal, e.g., 0.02 for 2 percent)')
    parser.add_argument('--n_portfolios', type=int, default=5000,
                       help='Number of random portfolios for frontier')
    
    args = parser.parse_args()
    
    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    print("=" * 60)
    print("SHARPE RATIO OPTIMIZER")
    print("=" * 60)
    
    # Download data
    prices = download_data(symbols, args.start, args.end)
    
    # Calculate log returns
    returns = calculate_log_returns(prices)
    print(f"\nCalculated log returns: {len(returns)} observations")
    
    # Initialize optimizer
    optimizer = SharpeOptimizer(returns, risk_free_rate=args.rf)
    
    # 1. Analytical tangency portfolio
    analytical_weights, analytical_metrics = optimizer.analytical_tangency_portfolio()
    
    # 2. Constrained optimization
    constrained_weights, constrained_metrics = optimizer.constrained_optimization()
    
    # 3. Generate efficient frontier
    frontier_df = optimizer.generate_efficient_frontier(n_portfolios=args.n_portfolios)
    
    # 4. Plot efficient frontier
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    plot_path = os.path.join(output_dir, 'frontier.png')
    
    optimizer.plot_efficient_frontier(
        frontier_df, 
        analytical_weights, 
        constrained_weights,
        save_path=plot_path
    )
    
    # 5. Save optimal weights
    weights_df = pd.DataFrame({
        'Symbol': symbols,
        'Analytical_Weights': analytical_weights,
        'Constrained_Weights': constrained_weights
    })
    weights_path = os.path.join(output_dir, 'optimal_weights.csv')
    weights_df.to_csv(weights_path, index=False)
    print(f"\nWeights saved to {weights_path}")
    
    print("\n" + "=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
