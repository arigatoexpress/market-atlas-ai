"""
Community Script Tester
Tests TradingView community scripts and indicators
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import hashlib

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScriptTestResult:
    """Result of testing a community script"""
    script_id: str
    script_name: str
    test_id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12])
    status: TestStatus = TestStatus.PENDING
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Test metrics
    load_time_ms: int = 0
    render_time_ms: int = 0
    error_count: int = 0
    warning_count: int = 0
    
    # Performance
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    
    # Quality assessment
    visual_quality: int = 0  # 1-10
    signal_accuracy: float = 0.0  # 0-1
    repaint_detected: bool = False
    lookahead_detected: bool = False
    
    # Comparison
    benchmark_comparison: Dict[str, Any] = field(default_factory=dict)
    
    # Logs
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def duration_seconds(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return (datetime.now() - self.started_at).total_seconds()


@dataclass
class CommunityScript:
    """Community script from TradingView"""
    id: str = ""
    name: str = ""
    author: str = ""
    source: str = "tradingview"  # tradingview, github, custom
    script_type: str = "indicator"  # indicator, strategy
    category: str = ""
    description: str = ""
    pine_code: str = ""
    pine_version: str = "v5"
    
    # Metadata
    rating: float = 0.0
    rating_count: int = 0
    installs: int = 0
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    
    # Testing
    is_tested: bool = False
    test_results: List[ScriptTestResult] = field(default_factory=list)
    overall_score: float = 0.0  # 0-100
    
    # Sapphire integration
    is_approved: bool = False
    approved_by: str = ""
    approved_at: Optional[datetime] = None
    recommended_symbols: List[str] = field(default_factory=list)
    recommended_timeframes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(f"{self.name}_{self.author}".encode()).hexdigest()[:12]


class CommunityScriptTester:
    """Tests community scripts for quality and performance"""
    
    def __init__(self, storage_path: str = "community_scripts"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.scripts: Dict[str, CommunityScript] = {}
        self.active_tests: Dict[str, ScriptTestResult] = {}
        self._load_scripts()
    
    def _load_scripts(self):
        """Load scripts from storage"""
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    script = CommunityScript(**data)
                    # Convert datetime strings
                    for field_name in ['created_date', 'updated_date', 'approved_at']:
                        val = getattr(script, field_name)
                        if isinstance(val, str):
                            setattr(script, field_name, datetime.fromisoformat(val))
                    # Convert test results
                    script.test_results = [
                        ScriptTestResult(**tr) if isinstance(tr, dict) else tr
                        for tr in script.test_results
                    ]
                    self.scripts[script.id] = script
            except Exception as e:
                logger.error(f"Error loading script {file_path}: {e}")
        
        logger.info(f"Loaded {len(self.scripts)} community scripts")
    
    def _save_script(self, script: CommunityScript):
        """Save script to disk"""
        file_path = self.storage_path / f"{script.id}.json"
        with open(file_path, 'w') as f:
            json.dump(asdict(script), f, indent=2, default=str)
    
    def add_script(self, name: str, pine_code: str, **kwargs) -> CommunityScript:
        """Add a new community script"""
        script = CommunityScript(
            name=name,
            pine_code=pine_code,
            author=kwargs.get('author', ''),
            source=kwargs.get('source', 'tradingview'),
            script_type=kwargs.get('script_type', 'indicator'),
            category=kwargs.get('category', ''),
            description=kwargs.get('description', ''),
            pine_version=kwargs.get('pine_version', 'v5'),
            rating=kwargs.get('rating', 0.0),
            rating_count=kwargs.get('rating_count', 0),
            installs=kwargs.get('installs', 0)
        )
        
        self.scripts[script.id] = script
        self._save_script(script)
        
        logger.info(f"Added community script: {name} ({script.id})")
        return script
    
    def get_script(self, script_id: str) -> Optional[CommunityScript]:
        """Get script by ID"""
        return self.scripts.get(script_id)
    
    def list_scripts(self, source: str = None, script_type: str = None, 
                     tested_only: bool = False, approved_only: bool = False) -> List[CommunityScript]:
        """List all scripts with filters"""
        scripts = list(self.scripts.values())
        
        if source:
            scripts = [s for s in scripts if s.source == source]
        
        if script_type:
            scripts = [s for s in scripts if s.script_type == script_type]
        
        if tested_only:
            scripts = [s for s in scripts if s.is_tested]
        
        if approved_only:
            scripts = [s for s in scripts if s.is_approved]
        
        return sorted(scripts, key=lambda s: s.overall_score, reverse=True)
    
    async def test_script(self, script_id: str, tv_controller, 
                         test_duration_seconds: int = 300) -> ScriptTestResult:
        """Test a community script"""
        script = self.scripts.get(script_id)
        if not script:
            raise ValueError(f"Script {script_id} not found")
        
        test_result = ScriptTestResult(
            script_id=script_id,
            script_name=script.name
        )
        
        self.active_tests[test_result.test_id] = test_result
        test_result.status = TestStatus.RUNNING
        
        logger.info(f"Starting test for script: {script.name}")
        
        try:
            # Test 1: Load script
            start_time = datetime.now()
            from app.core.tv_desktop_controller import PineScript
            
            pine_script = PineScript(
                name=script.name,
                code=script.pine_code,
                version=script.pine_version,
                category=script.script_type
            )
            
            success = await tv_controller.apply_pine_script(pine_script)
            test_result.load_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if not success:
                test_result.status = TestStatus.FAILED
                test_result.errors.append("Failed to load script into TradingView")
                return test_result
            
            # Wait for script to render
            await asyncio.sleep(3)
            test_result.render_time_ms = 3000
            
            # Test 2: Check for repaint/lookahead
            await self._detect_issues(tv_controller, test_result)
            
            # Test 3: Visual quality assessment (screenshot)
            screenshot = await tv_controller.capture_chart()
            if screenshot:
                # In a real implementation, use AI to assess visual quality
                test_result.visual_quality = 7  # Placeholder
            
            # Test 4: Test on multiple symbols/timeframes
            test_symbols = script.recommended_symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            test_timeframes = script.recommended_timeframes or ["1h", "4h", "1d"]
            
            for symbol in test_symbols[:3]:  # Test max 3 symbols
                await tv_controller.set_symbol(symbol)
                for tf in test_timeframes[:2]:  # Test max 2 timeframes
                    await tv_controller.set_timeframe(tf)
                    await asyncio.sleep(2)
                    
                    # Scan for signals
                    signals = await tv_controller.scan_for_signals()
                    if signals:
                        test_result.logs.append(f"Signals on {symbol} {tf}: {len(signals)}")
            
            # Calculate overall score
            test_result.overall_score = self._calculate_score(test_result)
            
            test_result.status = TestStatus.COMPLETED
            test_result.completed_at = datetime.now()
            
            # Update script
            script.test_results.append(test_result)
            script.is_tested = True
            script.overall_score = sum(r.overall_score for r in script.test_results) / len(script.test_results)
            self._save_script(script)
            
            logger.info(f"Test completed for script: {script.name} - Score: {test_result.overall_score}")
            
        except Exception as e:
            logger.error(f"Test failed for script {script.name}: {e}")
            test_result.status = TestStatus.FAILED
            test_result.errors.append(str(e))
        
        finally:
            if test_result.test_id in self.active_tests:
                del self.active_tests[test_result.test_id]
        
        return test_result
    
    async def _detect_issues(self, tv_controller, test_result: ScriptTestResult):
        """Detect repaint and lookahead issues"""
        try:
            # Take multiple screenshots over time
            screenshots = []
            for i in range(5):
                screenshot = await tv_controller.capture_chart()
                if screenshot:
                    screenshots.append(screenshot)
                await asyncio.sleep(1)
            
            # In a real implementation, compare screenshots to detect repaint
            # For now, use heuristics based on script code
            
            # Check for common repaint patterns
            if 'security(' in test_result.script_id.lower():
                code = self.scripts.get(test_result.script_id, CommunityScript()).pine_code
                if 'lookahead=' not in code.lower() or 'lookahead=barmerge.lookahead_on' in code.lower():
                    test_result.lookahead_detected = True
                    test_result.warnings.append("Possible lookahead bias detected")
            
            # Check for repaint patterns
            repaint_patterns = [
                r'\bhigh\[\s*\]',  # Using high without offset
                r'\blow\[\s*\]',   # Using low without offset
                r'\bclose\[\s*\]', # Using close without offset
            ]
            
            code = self.scripts.get(test_result.script_id, CommunityScript()).pine_code
            for pattern in repaint_patterns:
                if re.search(pattern, code):
                    test_result.repaint_detected = True
                    test_result.warnings.append("Possible repainting detected")
                    break
        
        except Exception as e:
            logger.error(f"Error detecting issues: {e}")
    
    def _calculate_score(self, test_result: ScriptTestResult) -> float:
        """Calculate overall test score"""
        score = 50.0  # Base score
        
        # Load time bonus (faster is better)
        if test_result.load_time_ms < 1000:
            score += 10
        elif test_result.load_time_ms < 3000:
            score += 5
        
        # Visual quality
        score += test_result.visual_quality * 2
        
        # Penalties
        if test_result.repaint_detected:
            score -= 20
        if test_result.lookahead_detected:
            score -= 15
        if test_result.error_count > 0:
            score -= test_result.error_count * 5
        
        return max(0, min(100, score))
    
    def approve_script(self, script_id: str, approved_by: str,
                       symbols: List[str] = None, timeframes: List[str] = None) -> bool:
        """Approve a script for use in Sapphire"""
        script = self.scripts.get(script_id)
        if not script:
            return False
        
        if not script.is_tested:
            logger.warning(f"Cannot approve untested script: {script_id}")
            return False
        
        if script.overall_score < 60:
            logger.warning(f"Cannot approve script with low score: {script.overall_score}")
            return False
        
        script.is_approved = True
        script.approved_by = approved_by
        script.approved_at = datetime.now()
        script.recommended_symbols = symbols or []
        script.recommended_timeframes = timeframes or ["1h", "4h"]
        
        self._save_script(script)
        
        logger.info(f"Approved script: {script.name} by {approved_by}")
        return True
    
    def reject_script(self, script_id: str, reason: str) -> bool:
        """Reject a script"""
        script = self.scripts.get(script_id)
        if not script:
            return False
        
        script.is_approved = False
        if script.test_results:
            script.test_results[-1].logs.append(f"Rejected: {reason}")
        
        self._save_script(script)
        return True
    
    def get_top_scripts(self, limit: int = 10, min_score: float = 70) -> List[CommunityScript]:
        """Get top-rated approved scripts"""
        scripts = [
            s for s in self.scripts.values()
            if s.is_approved and s.overall_score >= min_score
        ]
        return sorted(scripts, key=lambda s: s.overall_score, reverse=True)[:limit]
    
    def get_test_report(self, script_id: str) -> Optional[Dict]:
        """Get detailed test report for a script"""
        script = self.scripts.get(script_id)
        if not script:
            return None
        
        return {
            'script': {
                'id': script.id,
                'name': script.name,
                'author': script.author,
                'type': script.script_type,
                'rating': script.rating,
                'installs': script.installs
            },
            'test_summary': {
                'is_tested': script.is_tested,
                'is_approved': script.is_approved,
                'overall_score': script.overall_score,
                'test_count': len(script.test_results)
            },
            'test_results': [
                {
                    'test_id': r.test_id,
                    'status': r.status.value,
                    'duration': r.duration_seconds(),
                    'score': r.overall_score,
                    'load_time_ms': r.load_time_ms,
                    'visual_quality': r.visual_quality,
                    'repaint_detected': r.repaint_detected,
                    'lookahead_detected': r.lookahead_detected,
                    'errors': r.errors,
                    'logs': r.logs
                }
                for r in script.test_results
            ]
        }
    
    def get_active_tests(self) -> List[Dict]:
        """Get list of currently running tests"""
        return [
            {
                'test_id': t.test_id,
                'script_name': t.script_name,
                'status': t.status.value,
                'duration': t.duration_seconds()
            }
            for t in self.active_tests.values()
        ]


# Singleton
_tester: Optional[CommunityScriptTester] = None


def get_script_tester(storage_path: str = "community_scripts") -> CommunityScriptTester:
    """Get singleton script tester"""
    global _tester
    if _tester is None:
        _tester = CommunityScriptTester(storage_path)
    return _tester
