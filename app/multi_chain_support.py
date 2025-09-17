"""
Multi-Chain Support Module for Klerno Labs.

Provides comprehensive multi-blockchain support for Professional and Enterprise tiers.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SupportedChain(str, Enum):
    """Supported blockchain networks."""
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    XRP = "xrp"
    POLYGON = "polygon"
    BSC = "bsc"
    CARDANO = "cardano"
    SOLANA = "solana"
    AVALANCHE = "avalanche"
    LITECOIN = "litecoin"
    DOGECOIN = "dogecoin"

@dataclass
class ChainInfo:
    """Blockchain information."""
    name: str
    symbol: str
    explorer_url: str
    api_endpoint: str
    confirmations_required: int
    average_block_time: int  # seconds
    transaction_fee_unit: str
    supports_smart_contracts: bool
    native_token: str

@dataclass
class ChainTransaction:
    """Universal transaction structure for all chains."""
    chain: SupportedChain
    tx_hash: str
    from_address: str
    to_address: str
    amount: float
    fee: float
    timestamp: datetime
    block_number: Optional[int] = None
    confirmations: int = 0
    status: str = "pending"  # pending, confirmed, failed
    token_symbol: Optional[str] = None
    token_contract: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

@dataclass
class MultiChainAnalytics:
    """Cross-chain analytics data."""
    total_value_usd: float
    transaction_count: int
    unique_addresses: int
    chain_distribution: Dict[str, Dict[str, Any]]
    risk_metrics: Dict[str, float]
    timestamp: datetime

class MultiChainEngine:
    """Multi-blockchain support and analytics engine."""
    
    def __init__(self):
        self.chain_configs = self._initialize_chain_configs()
        self.rate_limiters = {}
        self._init_rate_limiting()
    
    def _initialize_chain_configs(self) -> Dict[SupportedChain, ChainInfo]:
        """Initialize blockchain configuration."""
        return {
            SupportedChain.BITCOIN: ChainInfo(
                name="Bitcoin",
                symbol="BTC",
                explorer_url="https://blockstream.info/tx/",
                api_endpoint="https://blockstream.info/api",
                confirmations_required=6,
                average_block_time=600,
                transaction_fee_unit="satoshi/byte",
                supports_smart_contracts=False,
                native_token="BTC"
            ),
            SupportedChain.ETHEREUM: ChainInfo(
                name="Ethereum",
                symbol="ETH",
                explorer_url="https://etherscan.io/tx/",
                api_endpoint="https://api.etherscan.io/api",
                confirmations_required=12,
                average_block_time=15,
                transaction_fee_unit="gwei",
                supports_smart_contracts=True,
                native_token="ETH"
            ),
            SupportedChain.XRP: ChainInfo(
                name="XRP Ledger",
                symbol="XRP",
                explorer_url="https://xrpscan.com/tx/",
                api_endpoint="https://s1.ripple.com:51234",
                confirmations_required=1,
                average_block_time=4,
                transaction_fee_unit="drops",
                supports_smart_contracts=True,
                native_token="XRP"
            ),
            SupportedChain.POLYGON: ChainInfo(
                name="Polygon",
                symbol="MATIC",
                explorer_url="https://polygonscan.com/tx/",
                api_endpoint="https://api.polygonscan.com/api",
                confirmations_required=12,
                average_block_time=2,
                transaction_fee_unit="gwei",
                supports_smart_contracts=True,
                native_token="MATIC"
            ),
            SupportedChain.BSC: ChainInfo(
                name="Binance Smart Chain",
                symbol="BNB",
                explorer_url="https://bscscan.com/tx/",
                api_endpoint="https://api.bscscan.com/api",
                confirmations_required=12,
                average_block_time=3,
                transaction_fee_unit="gwei",
                supports_smart_contracts=True,
                native_token="BNB"
            ),
            SupportedChain.CARDANO: ChainInfo(
                name="Cardano",
                symbol="ADA",
                explorer_url="https://cardanoscan.io/transaction/",
                api_endpoint="https://cardano-mainnet.blockfrost.io/api/v0",
                confirmations_required=15,
                average_block_time=20,
                transaction_fee_unit="lovelace",
                supports_smart_contracts=True,
                native_token="ADA"
            ),
            SupportedChain.SOLANA: ChainInfo(
                name="Solana",
                symbol="SOL",
                explorer_url="https://explorer.solana.com/tx/",
                api_endpoint="https://api.mainnet-beta.solana.com",
                confirmations_required=1,
                average_block_time=0.4,
                transaction_fee_unit="lamports",
                supports_smart_contracts=True,
                native_token="SOL"
            ),
            SupportedChain.AVALANCHE: ChainInfo(
                name="Avalanche",
                symbol="AVAX",
                explorer_url="https://snowtrace.io/tx/",
                api_endpoint="https://api.avax.network",
                confirmations_required=6,
                average_block_time=2,
                transaction_fee_unit="nAVAX",
                supports_smart_contracts=True,
                native_token="AVAX"
            )
        }
    
    def _init_rate_limiting(self):
        """Initialize rate limiting for API calls."""
        for chain in SupportedChain:
            self.rate_limiters[chain] = {
                "requests": 0,
                "reset_time": datetime.now(timezone.utc) + timedelta(minutes=1)
            }
    
    async def get_transaction(
        self, chain: SupportedChain, tx_hash: str
    ) -> Optional[ChainTransaction]:
        """Get transaction details from any supported chain."""
        
        if not self._check_rate_limit(chain):
            raise Exception(f"Rate limit exceeded for {chain.value}")
        
        try:
            if chain == SupportedChain.BITCOIN:
                return await self._get_bitcoin_transaction(tx_hash)
            elif chain == SupportedChain.ETHEREUM:
                return await self._get_ethereum_transaction(tx_hash)
            elif chain == SupportedChain.XRP:
                return await self._get_xrp_transaction(tx_hash)
            elif chain == SupportedChain.POLYGON:
                return await self._get_polygon_transaction(tx_hash)
            elif chain == SupportedChain.BSC:
                return await self._get_bsc_transaction(tx_hash)
            elif chain == SupportedChain.CARDANO:
                return await self._get_cardano_transaction(tx_hash)
            elif chain == SupportedChain.SOLANA:
                return await self._get_solana_transaction(tx_hash)
            elif chain == SupportedChain.AVALANCHE:
                return await self._get_avalanche_transaction(tx_hash)
            else:
                raise ValueError(f"Unsupported chain: {chain}")
                
        except Exception as e:
            logger.error(f"Error getting {chain.value} transaction {tx_hash}: {e}")
            return None
    
    async def get_address_transactions(
        self,
        chain: SupportedChain,
        address: str,
        limit: int = 100
    ) -> List[ChainTransaction]:
        """Get transactions for an address on any chain."""
        
        if not self._check_rate_limit(chain):
            raise Exception(f"Rate limit exceeded for {chain.value}")
        
        try:
            if chain == SupportedChain.BITCOIN:
                return await self._get_bitcoin_address_transactions(address, limit)
            elif chain == SupportedChain.ETHEREUM:
                return await self._get_ethereum_address_transactions(address, limit)
            elif chain == SupportedChain.XRP:
                return await self._get_xrp_address_transactions(address, limit)
            elif chain == SupportedChain.POLYGON:
                return await self._get_polygon_address_transactions(address, limit)
            elif chain == SupportedChain.BSC:
                return await self._get_bsc_address_transactions(address, limit)
            elif chain == SupportedChain.CARDANO:
                return await self._get_cardano_address_transactions(address, limit)
            elif chain == SupportedChain.SOLANA:
                return await self._get_solana_address_transactions(address, limit)
            elif chain == SupportedChain.AVALANCHE:
                return await self._get_avalanche_address_transactions(address, limit)
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting {chain.value} address transactions for {address}: {e}")
            return []
    
    async def analyze_cross_chain_activity(
        self,
        addresses: Dict[SupportedChain, List[str]],
        days: int = 30
    ) -> MultiChainAnalytics:
        """Analyze activity across multiple chains."""
        
        all_transactions = []
        chain_distribution = {}
        total_value_usd = 0.0
        unique_addresses = set()
        
        # Collect transactions from all chains
        for chain, addr_list in addresses.items():
            chain_txs = []
            chain_value = 0.0
            
            for address in addr_list:
                txs = await self.get_address_transactions(chain, address, limit=1000)
                
                # Filter by date range
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                recent_txs = [tx for tx in txs if tx.timestamp >= cutoff_date]
                
                chain_txs.extend(recent_txs)
                unique_addresses.add(address)
                
                # Calculate USD value (mock conversion)
                for tx in recent_txs:
                    chain_value += tx.amount * self._get_mock_usd_price(chain)
            
            all_transactions.extend(chain_txs)
            total_value_usd += chain_value
            
            chain_distribution[chain.value] = {
                "transaction_count": len(chain_txs),
                "total_value_usd": chain_value,
                "average_tx_value": chain_value / len(chain_txs) if chain_txs else 0,
                "addresses": len(addr_list)
            }
        
        # Calculate cross-chain risk metrics
        risk_metrics = self._calculate_cross_chain_risks(all_transactions, chain_distribution)
        
        return MultiChainAnalytics(
            total_value_usd=total_value_usd,
            transaction_count=len(all_transactions),
            unique_addresses=len(unique_addresses),
            chain_distribution=chain_distribution,
            risk_metrics=risk_metrics,
            timestamp=datetime.now(timezone.utc)
        )
    
    def get_supported_chains(self) -> List[Dict[str, Any]]:
        """Get list of all supported chains with their info."""
        chains = []
        for chain, info in self.chain_configs.items():
            chains.append({
                "chain": chain.value,
                "name": info.name,
                "symbol": info.symbol,
                "supports_smart_contracts": info.supports_smart_contracts,
                "average_block_time": info.average_block_time,
                "confirmations_required": info.confirmations_required
            })
        return chains
    
    def detect_chain_from_address(self, address: str) -> Optional[SupportedChain]:
        """Auto-detect blockchain from address format."""
        
        # Bitcoin patterns
        if (address.startswith('1') or address.startswith('3') or address.startswith('bc1')):
            return SupportedChain.BITCOIN
        
        # Ethereum/EVM patterns (40 hex chars after 0x)
        elif address.startswith('0x') and len(address) == 42:
            # Could be Ethereum, Polygon, BSC, or Avalanche
            # Default to Ethereum, but would need more context in real implementation
            return SupportedChain.ETHEREUM
        
        # XRP pattern
        elif address.startswith('r') and len(address) >= 25 and len(address) <= 34:
            return SupportedChain.XRP
        
        # Cardano pattern
        elif address.startswith('addr1'):
            return SupportedChain.CARDANO
        
        # Solana pattern (base58, 32-44 chars)
        elif len(address) >= 32 and len(address) <= 44 and address.isalnum():
            return SupportedChain.SOLANA
        
        return None
    
    def _check_rate_limit(self, chain: SupportedChain) -> bool:
        """Check if API call is within rate limits."""
        now = datetime.now(timezone.utc)
        limiter = self.rate_limiters[chain]
        
        if now > limiter["reset_time"]:
            limiter["requests"] = 0
            limiter["reset_time"] = now + timedelta(minutes=1)
        
        if limiter["requests"] >= 60:  # 60 requests per minute
            return False
        
        limiter["requests"] += 1
        return True
    
    def _get_mock_usd_price(self, chain: SupportedChain) -> float:
        """Get mock USD price for chain's native token."""
        # Mock prices - in production, use real price feeds
        prices = {
            SupportedChain.BITCOIN: 45000.0,
            SupportedChain.ETHEREUM: 3000.0,
            SupportedChain.XRP: 0.5,
            SupportedChain.POLYGON: 0.8,
            SupportedChain.BSC: 300.0,
            SupportedChain.CARDANO: 0.4,
            SupportedChain.SOLANA: 100.0,
            SupportedChain.AVALANCHE: 35.0
        }
        return prices.get(chain, 1.0)
    
    def _calculate_cross_chain_risks(
        self,
        transactions: List[ChainTransaction],
        chain_distribution: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate cross-chain risk metrics."""
        
        if not transactions:
            return {}
        
        # Chain concentration risk
        total_chains = len(chain_distribution)
        concentration_risk = 1.0 - (total_chains / len(SupportedChain))
        
        # Volume concentration
        total_value = sum(dist["total_value_usd"] for dist in chain_distribution.values())
        max_chain_value = max(dist["total_value_usd"] for dist in chain_distribution.values())
        volume_concentration = max_chain_value / total_value if total_value > 0 else 0
        
        # Transaction frequency risk
        avg_daily_txs = len(transactions) / 30  # Assuming 30-day analysis
        frequency_risk = min(1.0, avg_daily_txs / 100)  # Normalize to 0-1
        
        # Cross-chain movement detection
        cross_chain_movements = 0
        # This would analyze transaction patterns to detect funds moving between chains
        # For now, mock calculation
        cross_chain_movements = len(transactions) * 0.1  # 10% assumed cross-chain
        cross_chain_risk = min(1.0, cross_chain_movements / len(transactions))
        
        return {
            "concentration_risk": concentration_risk,
            "volume_concentration": volume_concentration,
            "frequency_risk": frequency_risk,
            "cross_chain_risk": cross_chain_risk,
            "overall_risk": (
                concentration_risk
                + volume_concentration
                + frequency_risk
                + cross_chain_risk
            ) / 4
        }
    
    # Mock implementation methods for different chains
    # In production, these would make real API calls
    
    async def _get_bitcoin_transaction(self, tx_hash: str) -> ChainTransaction:
        """Mock Bitcoin transaction fetch."""
        await asyncio.sleep(0.1)  # Simulate API delay
        
        return ChainTransaction(
            chain=SupportedChain.BITCOIN,
            tx_hash=tx_hash,
            from_address="1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
            to_address="3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
            amount=0.01,
            fee=0.0001,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
            block_number=700000,
            confirmations=6,
            status="confirmed"
        )
    
    async def _get_ethereum_transaction(self, tx_hash: str) -> ChainTransaction:
        """Mock Ethereum transaction fetch."""
        await asyncio.sleep(0.1)
        
        return ChainTransaction(
            chain=SupportedChain.ETHEREUM,
            tx_hash=tx_hash,
            from_address="0x742d35cc6634c0532925a3b8d98c5b49e1c5b321",
            to_address="0x8ba1f109551bd432803012645hac136c1c25a9ba",
            amount=1.5,
            fee=0.005,
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=30),
            block_number=18000000,
            confirmations=12,
            status="confirmed"
        )
    
    async def _get_xrp_transaction(self, tx_hash: str) -> ChainTransaction:
        """Mock XRP transaction fetch."""
        await asyncio.sleep(0.1)
        
        return ChainTransaction(
            chain=SupportedChain.XRP,
            tx_hash=tx_hash,
            from_address="rDNvprzgL4d3Fgi3rWHHNz3j9n8x76LdQj",
            to_address="rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe",
            amount=100.0,
            fee=0.00001,
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
            block_number=75000000,
            confirmations=1,
            status="confirmed"
        )
    
    # Placeholder methods for other chains
    async def _get_polygon_transaction(self, tx_hash: str) -> ChainTransaction:
        await asyncio.sleep(0.1)
        return await self._get_ethereum_transaction(tx_hash)  # Similar to Ethereum
    
    async def _get_bsc_transaction(self, tx_hash: str) -> ChainTransaction:
        await asyncio.sleep(0.1)
        return await self._get_ethereum_transaction(tx_hash)  # Similar to Ethereum
    
    async def _get_cardano_transaction(self, tx_hash: str) -> ChainTransaction:
        await asyncio.sleep(0.1)
        return ChainTransaction(
            chain=SupportedChain.CARDANO,
            tx_hash=tx_hash,
            from_address="addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzern",
            to_address="addr1qy99gk2vr8j8ez5wy6x7q8j8ez5wy6x7q8j8ez5wy6x7",
            amount=50.0,
            fee=0.2,
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=20),
            confirmations=15,
            status="confirmed"
        )
    
    async def _get_solana_transaction(self, tx_hash: str) -> ChainTransaction:
        await asyncio.sleep(0.1)
        return ChainTransaction(
            chain=SupportedChain.SOLANA,
            tx_hash=tx_hash,
            from_address="11111111111111111111111111111112",
            to_address="11111111111111111111111111111113",
            amount=2.5,
            fee=0.000005,
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=30),
            confirmations=1,
            status="confirmed"
        )
    
    async def _get_avalanche_transaction(self, tx_hash: str) -> ChainTransaction:
        await asyncio.sleep(0.1)
        return await self._get_ethereum_transaction(tx_hash)  # Similar to Ethereum
    
    # Address transaction methods (simplified - would return lists)
    async def _get_bitcoin_address_transactions(
        self, address: str, limit: int
    ) -> List[ChainTransaction]:
        return [await self._get_bitcoin_transaction(f"mock_tx_{i}") for i in range(min(limit, 10))]
    
    async def _get_ethereum_address_transactions(
        self, address: str, limit: int
    ) -> List[ChainTransaction]:
        return [await self._get_ethereum_transaction(f"mock_tx_{i}") for i in range(min(limit, 10))]
    
    async def _get_xrp_address_transactions(
        self, address: str, limit: int
    ) -> List[ChainTransaction]:
        return [await self._get_xrp_transaction(f"mock_tx_{i}") for i in range(min(limit, 10))]
    
    async def _get_polygon_address_transactions(
        self, address: str, limit: int
    ) -> List[ChainTransaction]:
        return [await self._get_polygon_transaction(f"mock_tx_{i}") for i in range(min(limit, 10))]
    
    async def _get_bsc_address_transactions(
        self, address: str, limit: int
    ) -> List[ChainTransaction]:
        return [await self._get_bsc_transaction(f"mock_tx_{i}") for i in range(min(limit, 10))]
    
    async def _get_cardano_address_transactions(
        self, address: str, limit: int
    ) -> List[ChainTransaction]:
        return [await self._get_cardano_transaction(f"mock_tx_{i}") for i in range(min(limit, 10))]
    
    async def _get_solana_address_transactions(
        self, address: str, limit: int
    ) -> List[ChainTransaction]:
        return [await self._get_solana_transaction(f"mock_tx_{i}") for i in range(min(limit, 10))]
    
    async def _get_avalanche_address_transactions(
        self, address: str, limit: int
    ) -> List[ChainTransaction]:
        return [
            await self._get_avalanche_transaction(f"mock_tx_{i}")
            for i in range(min(limit, 10))
        ]

# Global multi-chain engine
multi_chain_engine = MultiChainEngine()

async def get_transaction(chain: SupportedChain, tx_hash: str) -> Optional[ChainTransaction]:
    """Get transaction from any supported chain."""
    return await multi_chain_engine.get_transaction(chain, tx_hash)

async def get_address_transactions(
    chain: SupportedChain, address: str, limit: int = 100
) -> List[ChainTransaction]:
    """Get transactions for address on any chain."""
    return await multi_chain_engine.get_address_transactions(chain, address, limit)

async def analyze_cross_chain_activity(
    addresses: Dict[SupportedChain, List[str]], days: int = 30
) -> MultiChainAnalytics:
    """Analyze cross-chain activity."""
    return await multi_chain_engine.analyze_cross_chain_activity(addresses, days)

def get_supported_chains() -> List[Dict[str, Any]]:
    """Get all supported blockchain networks."""
    return multi_chain_engine.get_supported_chains()

def detect_chain_from_address(address: str) -> Optional[SupportedChain]:
    """Auto-detect blockchain from address format."""
    return multi_chain_engine.detect_chain_from_address(address)

def is_multichain_feature_available(user_tier: str) -> bool:
    """Check if user has access to multi-chain features."""
    return user_tier.lower() in ['professional', 'enterprise']