"""
Database Module for Trade Tracking
"""
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger

Base = declarative_base()

class Trade(Base):
    """Trade record model"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    strategy = Column(String(50))
    side = Column(String(10), nullable=False)  # buy/sell
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    size = Column(Float, nullable=False)
    leverage = Column(Integer, default=1)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime)
    pnl = Column(Float)
    pnl_percentage = Column(Float)
    fee = Column(Float)
    status = Column(String(20), default='open')  # open, closed, cancelled
    exit_reason = Column(String(100))
    order_id = Column(String(100))
    
    def to_dict(self) -> Dict:
        """Convert trade to dictionary"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'strategy': self.strategy,
            'side': self.side,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'size': self.size,
            'leverage': self.leverage,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'pnl': self.pnl,
            'pnl_percentage': self.pnl_percentage,
            'fee': self.fee,
            'status': self.status,
            'exit_reason': self.exit_reason,
            'order_id': self.order_id
        }


class Performance(Base):
    """Performance metrics model"""
    __tablename__ = 'performance'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    total_pnl_percentage = Column(Float, default=0.0)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    avg_win = Column(Float)
    avg_loss = Column(Float)
    profit_factor = Column(Float)
    portfolio_value = Column(Float)
    
    def to_dict(self) -> Dict:
        """Convert performance to dictionary"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'total_pnl_percentage': self.total_pnl_percentage,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'portfolio_value': self.portfolio_value
        }


class Database:
    """Database manager for trade tracking"""
    
    def __init__(self, database_url: str):
        """Initialize database connection"""
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        logger.info(f"Database initialized: {database_url}")
    
    def add_trade(self, trade_data: Dict) -> Trade:
        """Add new trade to database"""
        trade = Trade(**trade_data)
        self.session.add(trade)
        self.session.commit()
        logger.info(f"Trade added: {trade.symbol} {trade.side} @ {trade.entry_price}")
        return trade
    
    def update_trade(self, trade_id: int, update_data: Dict) -> Optional[Trade]:
        """Update existing trade"""
        trade = self.session.query(Trade).filter_by(id=trade_id).first()
        if trade:
            for key, value in update_data.items():
                setattr(trade, key, value)
            self.session.commit()
            logger.info(f"Trade {trade_id} updated")
            return trade
        return None
    
    def close_trade(self, trade_id: int, exit_price: float, exit_reason: str = 'manual') -> Optional[Trade]:
        """Close a trade"""
        trade = self.session.query(Trade).filter_by(id=trade_id).first()
        if trade and trade.status == 'open':
            trade.exit_price = exit_price
            trade.exit_time = datetime.utcnow()
            trade.status = 'closed'
            trade.exit_reason = exit_reason
            
            # Calculate P&L
            if trade.side == 'buy':
                pnl = (exit_price - trade.entry_price) * trade.size * trade.leverage
                pnl_pct = ((exit_price - trade.entry_price) / trade.entry_price) * trade.leverage
            else:
                pnl = (trade.entry_price - exit_price) * trade.size * trade.leverage
                pnl_pct = ((trade.entry_price - exit_price) / trade.entry_price) * trade.leverage
            
            trade.pnl = pnl
            trade.pnl_percentage = pnl_pct
            
            self.session.commit()
            logger.info(f"Trade {trade_id} closed: P&L = {pnl:.2f} ({pnl_pct:.2%})")
            return trade
        return None
    
    def get_open_trades(self) -> List[Trade]:
        """Get all open trades"""
        return self.session.query(Trade).filter_by(status='open').all()
    
    def get_closed_trades(self, limit: int = 100) -> List[Trade]:
        """Get recent closed trades"""
        return self.session.query(Trade).filter_by(status='closed').order_by(Trade.exit_time.desc()).limit(limit).all()
    
    def get_trade_by_id(self, trade_id: int) -> Optional[Trade]:
        """Get trade by ID"""
        return self.session.query(Trade).filter_by(id=trade_id).first()
    
    def get_trade_by_order_id(self, order_id: str) -> Optional[Trade]:
        """Get trade by order ID"""
        return self.session.query(Trade).filter_by(order_id=order_id).first()
    
    def calculate_performance(self) -> Dict:
        """Calculate performance metrics"""
        closed_trades = self.get_closed_trades(limit=1000)
        
        if not closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0
            }
        
        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl and t.pnl < 0]
        
        total_pnl = sum([t.pnl for t in closed_trades if t.pnl])
        total_wins = sum([t.pnl for t in winning_trades])
        total_losses = abs(sum([t.pnl for t in losing_trades]))
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        avg_win = total_wins / len(winning_trades) if winning_trades else 0
        avg_loss = total_losses / len(losing_trades) if losing_trades else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        }
    
    def save_performance(self, metrics: Dict) -> Performance:
        """Save performance snapshot"""
        perf = Performance(**metrics)
        self.session.add(perf)
        self.session.commit()
        return perf
    
    def get_latest_performance(self) -> Optional[Performance]:
        """Get latest performance record"""
        return self.session.query(Performance).order_by(Performance.timestamp.desc()).first()
    
    def close(self):
        """Close database connection"""
        self.session.close()
