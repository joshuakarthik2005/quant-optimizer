"""
Utility functions for portfolio optimization and data processing.

This module provides helper functions for:
- Downloading historical price data
- Computing log returns
- Annualizing returns and covariance matrices
- Calculating performance metrics
"""

import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Tuple


def download_data(symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    """
    Download historical adjusted close prices for given symbols.
    
    Parameters:
    -----------
    symbols : list of str
        List of ticker symbols (e.g., ['SPY', 'GLD', 'AGG'])
    start_date : str
        Start date in format 'YYYY-MM-DD'
    end_date : str
        End date in format 'YYYY-MM-DD'
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with adjusted close prices, columns are symbols
    """
    print(f"Downloading data for {symbols} from {start_date} to {end_date}...")
    
    # Download data
    data = yf.download(symbols, start=start_date, end=end_date, progress=False, auto_adjust=True)
    
    # Handle different yfinance return formats
    if 'Close' in data.columns:
        # Multi-level columns
        if isinstance(data.columns, pd.MultiIndex):
            data = data['Close']
        else:
            data = data[['Close']].copy()
            data.columns = symbols
    elif len(symbols) == 1:
        # Single symbol, simpler structure
        data = data[['Close']].copy()
        data.columns = symbols
    else:
        # Already in correct format
        pass
    
    # If single symbol, ensure it's a DataFrame
    if isinstance(data, pd.Series):
        data = data.to_frame(name=symbols[0])
    
    # Drop any rows with NaN values
    data = data.dropna()
    print(f"Downloaded {len(data)} rows of data")
    return data


def calculate_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate log returns from price data.
    
    Log returns: r_t = ln(P_t / P_{t-1})
    
    Parameters:
    -----------
    prices : pd.DataFrame
        DataFrame with price data
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with log returns
    """
    returns = np.log(prices / prices.shift(1))
    return returns.dropna()


def annualize_returns(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    Annualize returns.
    
    Formula: R_annual = mean(returns) * periods_per_year
    
    Parameters:
    -----------
    returns : pd.Series
        Series of returns
    periods_per_year : int
        Number of periods per year (252 for daily data)
    
    Returns:
    --------
    float
        Annualized return
    """
    return returns.mean() * periods_per_year


def annualize_covariance(cov_matrix: pd.DataFrame, periods_per_year: int = 252) -> pd.DataFrame:
    """
    Annualize covariance matrix.
    
    Formula: Σ_annual = Σ_daily * periods_per_year
    
    Parameters:
    -----------
    cov_matrix : pd.DataFrame
        Covariance matrix
    periods_per_year : int
        Number of periods per year (252 for daily data)
    
    Returns:
    --------
    pd.DataFrame
        Annualized covariance matrix
    """
    return cov_matrix * periods_per_year


def calculate_portfolio_return(weights: np.ndarray, mean_returns: np.ndarray) -> float:
    """
    Calculate portfolio expected return.
    
    Formula: R_p = w^T * μ
    
    Parameters:
    -----------
    weights : np.ndarray
        Portfolio weights (must sum to 1)
    mean_returns : np.ndarray
        Expected returns for each asset
    
    Returns:
    --------
    float
        Portfolio expected return
    """
    return np.dot(weights, mean_returns)


def calculate_portfolio_volatility(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
    """
    Calculate portfolio volatility (standard deviation).
    
    Formula: σ_p = sqrt(w^T * Σ * w)
    
    Parameters:
    -----------
    weights : np.ndarray
        Portfolio weights (must sum to 1)
    cov_matrix : np.ndarray
        Covariance matrix of returns
    
    Returns:
    --------
    float
        Portfolio volatility (annualized standard deviation)
    """
    variance = np.dot(weights.T, np.dot(cov_matrix, weights))
    return np.sqrt(variance)


def calculate_sharpe_ratio(weights: np.ndarray, mean_returns: np.ndarray, 
                          cov_matrix: np.ndarray, risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio.
    
    Formula: S(w) = (w^T * μ - r_f) / sqrt(w^T * Σ * w)
    
    Parameters:
    -----------
    weights : np.ndarray
        Portfolio weights (must sum to 1)
    mean_returns : np.ndarray
        Expected returns for each asset
    cov_matrix : np.ndarray
        Covariance matrix of returns
    risk_free_rate : float
        Risk-free rate (annualized)
    
    Returns:
    --------
    float
        Sharpe ratio
    """
    portfolio_return = calculate_portfolio_return(weights, mean_returns)
    portfolio_vol = calculate_portfolio_volatility(weights, cov_matrix)
    
    if portfolio_vol == 0:
        return 0.0
    
    return (portfolio_return - risk_free_rate) / portfolio_vol


def calculate_max_drawdown(returns: pd.Series) -> float:
    """
    Calculate maximum drawdown.
    
    Maximum drawdown is the largest peak-to-trough decline.
    
    Parameters:
    -----------
    returns : pd.Series
        Series of returns
    
    Returns:
    --------
    float
        Maximum drawdown (as a positive decimal, e.g., 0.15 for 15% drawdown)
    """
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return abs(drawdown.min())


def calculate_turnover(old_weights: np.ndarray, new_weights: np.ndarray) -> float:
    """
    Calculate portfolio turnover.
    
    Turnover = sum(|w_new - w_old|) / 2
    
    Parameters:
    -----------
    old_weights : np.ndarray
        Old portfolio weights
    new_weights : np.ndarray
        New portfolio weights
    
    Returns:
    --------
    float
        Portfolio turnover (0 to 1)
    """
    return np.sum(np.abs(new_weights - old_weights)) / 2


def apply_transaction_costs(returns: pd.Series, turnover: float, cost_bps: float = 10.0) -> pd.Series:
    """
    Apply transaction costs to returns.
    
    Cost = turnover * (cost_bps / 10000)
    
    Parameters:
    -----------
    returns : pd.Series
        Series of returns
    turnover : float
        Portfolio turnover (0 to 1)
    cost_bps : float
        Transaction cost in basis points (10 bps = 0.1%)
    
    Returns:
    --------
    pd.Series
        Returns after transaction costs
    """
    cost = turnover * (cost_bps / 10000)
    return returns - cost


def get_performance_metrics(returns: pd.Series, periods_per_year: int = 252) -> dict:
    """
    Calculate comprehensive performance metrics.
    
    Parameters:
    -----------
    returns : pd.Series
        Series of returns
    periods_per_year : int
        Number of periods per year (252 for daily data)
    
    Returns:
    --------
    dict
        Dictionary with performance metrics
    """
    annual_return = annualize_returns(returns, periods_per_year)
    annual_vol = returns.std() * np.sqrt(periods_per_year)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0.0
    max_dd = calculate_max_drawdown(returns)
    cumulative_return = (1 + returns).prod() - 1
    
    return {
        'Annual Return': annual_return,
        'Annual Volatility': annual_vol,
        'Sharpe Ratio': sharpe,
        'Max Drawdown': max_dd,
        'Cumulative Return': cumulative_return,
        'Total Days': len(returns)
    }
