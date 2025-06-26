"""
RTSI算法 - 评级趋势强度指数 (Rating Trend Strength Index)

核心功能：
1. 个股评级趋势强度计算
2. 趋势方向性、一致性、持续性、幅度综合分析
3. 批量计算和排名功能

算法原理：
- 方向性：线性回归斜率
- 一致性：R²值 
- 显著性：p值检验
- 幅度：标准化变化幅度
- RTSI指数：综合评分 (0-100)

作者: 267278466@qq.com
创建时间：2025-06-07
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional, Union
import warnings
from datetime import datetime

# 导入配置
try:
    from config import RATING_SCORE_MAP
except ImportError:
    # 如果无法导入配置，使用默认映射
    RATING_SCORE_MAP = {
        '大多': 7, '中多': 6, '小多': 5, '微多': 4,
        '微空': 3, '小空': 2, '中空': 1, '大空': 0, 
        '-': None
    }

# 抑制scipy的警告
warnings.filterwarnings('ignore', category=RuntimeWarning)


def calculate_rating_trend_strength_index(stock_ratings: pd.Series) -> Dict[str, Union[float, str, int, None]]:
    """
    评级趋势强度指数 (Rating Trend Strength Index)
    综合考虑：方向性、一致性、持续性、幅度
    
    参数:
        stock_ratings (pd.Series): 股票评级序列，索引为日期，值为评级
        
    返回:
        dict: {
            'rtsi': float,              # RTSI指数 (0-100)
            'trend': str,               # 趋势方向
            'confidence': float,        # 置信度 (0-1)
            'slope': float,             # 回归斜率
            'r_squared': float,         # R²值
            'recent_score': int,        # 最新评级分数
            'score_change_5d': float,   # 5日变化
            'data_points': int,         # 有效数据点数
            'calculation_time': str     # 计算时间
        }
    """
    calculation_start = datetime.now()
    
    # 1. 数据预处理
    if stock_ratings is None or len(stock_ratings) == 0:
        return _get_insufficient_data_result()
    
    # 将评级转换为分数
    scores = stock_ratings.map(RATING_SCORE_MAP).dropna()
    
    if len(scores) < 5:
        return _get_insufficient_data_result(len(scores))
    
    try:
        # 2. 线性回归分析 - 趋势方向性
        x = np.arange(len(scores))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, scores)
        
        # 3. 趋势一致性 (R²值)
        consistency = r_value ** 2
        
        # 4. 趋势显著性 (p值检验)
        significance = max(0, 1 - p_value) if p_value < 0.05 else 0
        
        # 5. 变化幅度 (标准化到8级评级范围: 0-7)
        rating_scale_max = 7  # 8级评级系统：大多=7到大空=0
        amplitude = abs(slope) * len(scores) / rating_scale_max
        amplitude = min(amplitude, 1.0)  # 限制在[0,1]范围
        
        # 6. 综合RTSI指数计算 (0-100)
        # 权重分配：一致性40% + 显著性30% + 幅度30%
        rtsi = (consistency * 0.4 + significance * 0.3 + amplitude * 0.3) * 100
        
        # 7. 趋势方向判断
        trend_direction = _determine_trend_direction(slope, significance)
        
        # 8. 计算附加指标
        recent_score = int(scores.iloc[-1]) if len(scores) > 0 else None
        score_change_5d = _calculate_score_change(scores, 5)
        
        # 9. 计算时间
        calculation_time = f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
        
        return {
            'rtsi': round(rtsi, 2),
            'trend': trend_direction,
            'confidence': round(significance, 3),
            'slope': round(slope, 4),
            'r_squared': round(consistency, 3),
            'recent_score': recent_score,
            'score_change_5d': score_change_5d,
            'data_points': len(scores),
            'calculation_time': calculation_time
        }
        
    except Exception as e:
        return {
            'rtsi': 0,
            'trend': 'calculation_error',
            'confidence': 0,
            'error': str(e),
            'data_points': len(scores),
            'calculation_time': f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
        }


def batch_calculate_rtsi(stock_data: pd.DataFrame) -> Dict[str, Dict]:
    """
    批量计算所有股票的RTSI指数
    
    参数:
        stock_data (pd.DataFrame): 股票数据，列包含股票代码、名称和各日期评级
        
    返回:
        dict: {stock_code: rtsi_result, ...}
    """
    if stock_data is None or len(stock_data) == 0:
        return {}
    
    batch_start = datetime.now()
    results = {}
    
    # 识别日期列
    date_columns = [col for col in stock_data.columns if str(col).startswith('202')]
    date_columns.sort()  # 确保日期排序
    
    if len(date_columns) == 0:
        print("警告 警告：未找到有效的日期列")
        return {}
    
    print(f"数据 开始批量计算RTSI指数...")
    print(f"   数据规模: {len(stock_data)} 只股票 × {len(date_columns)} 个交易日")
    
    # 批量处理
    for idx, row in stock_data.iterrows():
        stock_code = str(row.get('股票代码', f'STOCK_{idx}'))
        stock_name = row.get('股票名称', '未知股票')
        
        # 提取该股票的评级序列
        stock_ratings = row[date_columns]
        
        # 计算RTSI
        rtsi_result = calculate_rating_trend_strength_index(stock_ratings)
        
        # 添加股票基本信息
        rtsi_result.update({
            'stock_code': stock_code,
            'stock_name': stock_name,
            'industry': row.get('行业', '未分类')
        })
        
        results[stock_code] = rtsi_result
        
        # 进度提示
        if (idx + 1) % 1000 == 0:
            print(f"   已处理: {idx + 1:,} / {len(stock_data):,} 只股票")
    
    batch_time = (datetime.now() - batch_start).total_seconds()
    print(f"成功 批量计算完成: {len(results)} 只股票，耗时 {batch_time:.2f} 秒")
    print(f"   平均速度: {len(results) / batch_time:.1f} 只/秒")
    
    return results


def get_rtsi_ranking(rtsi_results: Dict[str, Dict], top_n: int = 50, 
                    trend_filter: Optional[str] = None) -> List[Tuple[str, str, float, str]]:
    """
    获取RTSI指数排名
    
    参数:
        rtsi_results (dict): 批量计算的RTSI结果
        top_n (int): 返回前N名，默认50
        trend_filter (str): 趋势过滤器，可选值: 'up', 'down', 'strong_up', 'strong_down'
        
    返回:
        list: [(stock_code, stock_name, rtsi, trend), ...] 按RTSI降序排列
    """
    if not rtsi_results:
        return []
    
    # 过滤有效结果
    valid_results = []
    for stock_code, result in rtsi_results.items():
        if result.get('rtsi', 0) > 0:  # 排除计算失败的结果
            # 趋势过滤
            if trend_filter:
                trend = result.get('trend', '')
                if trend_filter == 'up' and 'up' not in trend:
                    continue
                elif trend_filter == 'down' and 'down' not in trend:
                    continue
                elif trend_filter == 'strong_up' and trend != 'strong_up':
                    continue
                elif trend_filter == 'strong_down' and trend != 'strong_down':
                    continue
            
            valid_results.append((
                stock_code,
                result.get('stock_name', '未知'),
                result.get('rtsi', 0),
                result.get('trend', 'unknown'),
                result.get('confidence', 0),
                result.get('recent_score', 0)
            ))
    
    # 按RTSI指数降序排序
    valid_results.sort(key=lambda x: x[2], reverse=True)
    
    # 返回前N名
    return [(code, name, rtsi, trend) for code, name, rtsi, trend, conf, score in valid_results[:top_n]]


def get_rtsi_statistics(rtsi_results: Dict[str, Dict]) -> Dict[str, Union[int, float]]:
    """
    获取RTSI计算的统计信息
    
    参数:
        rtsi_results (dict): 批量计算的RTSI结果
        
    返回:
        dict: 统计信息
    """
    if not rtsi_results:
        return {}
    
    valid_rtsi = [result['rtsi'] for result in rtsi_results.values() 
                  if result.get('rtsi', 0) > 0]
    
    if not valid_rtsi:
        return {'total_stocks': len(rtsi_results), 'valid_calculations': 0}
    
    # 趋势分布统计
    trend_counts = {}
    for result in rtsi_results.values():
        trend = result.get('trend', 'unknown')
        trend_counts[trend] = trend_counts.get(trend, 0) + 1
    
    return {
        'total_stocks': len(rtsi_results),
        'valid_calculations': len(valid_rtsi),
        'success_rate': len(valid_rtsi) / len(rtsi_results) * 100,
        'rtsi_mean': np.mean(valid_rtsi),
        'rtsi_median': np.median(valid_rtsi),
        'rtsi_std': np.std(valid_rtsi),
        'rtsi_max': max(valid_rtsi),
        'rtsi_min': min(valid_rtsi),
        'trend_distribution': trend_counts
    }


# 私有辅助函数

def _get_insufficient_data_result(data_points: int = 0) -> Dict:
    """返回数据不足的结果"""
    return {
        'rtsi': 0,
        'trend': 'insufficient_data',
        'confidence': 0,
        'slope': 0,
        'r_squared': 0,
        'recent_score': None,
        'score_change_5d': None,
        'data_points': data_points,
        'calculation_time': '0.001s'
    }


def _determine_trend_direction(slope: float, significance: float) -> str:
    """
    根据斜率和显著性确定趋势方向 - 优化版本
    采用统一的7级分类标准，基于统计学原理
    
    参数:
        slope (float): 回归斜率
        significance (float): 显著性水平
        
    返回:
        str: 趋势方向描述（统一标准）
    """
    # 先计算基础RTSI分数用于分类
    if significance < 0.3:  # 显著性太低，归为横盘
        return 'neutral'
    
    # 基于斜率强度和显著性的组合判断
    if slope > 0.15 and significance > 0.7:
        return 'strong_bull'      # 强势多头趋势
    elif slope > 0.08 and significance > 0.5:
        return 'moderate_bull'    # 温和多头趋势
    elif slope > 0.03:
        return 'weak_bull'        # 弱势多头格局
    elif slope < -0.15 and significance > 0.7:
        return 'strong_bear'      # 强势空头趋势
    elif slope < -0.08 and significance > 0.5:
        return 'moderate_bear'    # 温和空头趋势
    elif slope < -0.03:
        return 'weak_bear'        # 弱势空头格局
    else:
        return 'neutral'          # 横盘整理格局


def classify_rtsi_by_value(rtsi_value: float) -> str:
    """
    根据RTSI数值进行统一分类 - 新增函数
    采用基于统计学分析的7级分类标准
    
    参数:
        rtsi_value (float): RTSI指数值 (0-100)
        
    返回:
        str: 统一的趋势分类
    """
    if rtsi_value >= 75:
        return 'strong_bull'      # 强势多头：统计学上位数(90%+)
    elif rtsi_value >= 60:
        return 'moderate_bull'    # 温和多头：上四分位数(75%+)
    elif rtsi_value >= 50:
        return 'weak_bull'        # 弱势多头：中位数以上
    elif rtsi_value >= 40:
        return 'neutral'          # 横盘整理：中性区间
    elif rtsi_value >= 30:
        return 'weak_bear'        # 弱势空头：下四分位数(25%+)
    elif rtsi_value >= 20:
        return 'moderate_bear'    # 温和空头：较低分位数
    else:
        return 'strong_bear'      # 强势空头：最低分位数


def get_professional_terminology(trend_category: str) -> dict:
    """
    获取专业术语描述 - 新增函数
    
    参数:
        trend_category (str): 趋势分类
        
    返回:
        dict: 包含简短和详细描述的专业术语
    """
    terminology = {
        'strong_bull': {
            'short': '强势多头',
            'detailed': '强势多头趋势，技术面极度乐观，建议积极配置',
            'english': 'Strong Bullish Trend',
            'confidence_required': 0.7
        },
        'moderate_bull': {
            'short': '温和多头', 
            'detailed': '温和多头趋势，上升动能充足，适合中线持有',
            'english': 'Moderate Bullish Trend',
            'confidence_required': 0.5
        },
        'weak_bull': {
            'short': '弱势多头',
            'detailed': '弱势多头格局，上升空间有限，谨慎乐观',
            'english': 'Weak Bullish Bias',
            'confidence_required': 0.4
        },
        'neutral': {
            'short': '横盘整理',
            'detailed': '横盘整理格局，方向选择待定，观望为主',
            'english': 'Sideways Consolidation',
            'confidence_required': 0.3
        },
        'weak_bear': {
            'short': '弱势空头',
            'detailed': '弱势空头格局，下跌空间有限，适度防御',
            'english': 'Weak Bearish Bias', 
            'confidence_required': 0.4
        },
        'moderate_bear': {
            'short': '温和空头',
            'detailed': '温和空头趋势，下跌动能充足，建议减仓',
            'english': 'Moderate Bearish Trend',
            'confidence_required': 0.5
        },
        'strong_bear': {
            'short': '强势空头',
            'detailed': '强势空头趋势，技术面极度悲观，严格风控',
            'english': 'Strong Bearish Trend',
            'confidence_required': 0.7
        }
    }
    
    return terminology.get(trend_category, {
        'short': '未知趋势',
        'detailed': '趋势方向不明确，建议谨慎操作',
        'english': 'Unknown Trend',
        'confidence_required': 0.5
    })


def calculate_risk_level_unified(rtsi_value: float, confidence: float) -> str:
    """
    统一的风险等级评估 - 新增函数
    基于RTSI值和置信度的综合评估
    
    参数:
        rtsi_value (float): RTSI指数值
        confidence (float): 置信度
        
    返回:
        str: 风险等级描述
    """
    # 基于RTSI值和置信度的矩阵评估
    if rtsi_value >= 75 and confidence >= 0.7:
        return '🟢 极低风险（强势确认）'
    elif rtsi_value >= 75 and confidence >= 0.4:
        return '🟡 中等风险（强势待确认）'
    elif rtsi_value >= 60 and confidence >= 0.5:
        return '🟢 低风险（温和上升）'
    elif rtsi_value >= 50 and confidence >= 0.4:
        return '🟡 中等风险（弱势多头）'
    elif rtsi_value >= 40:
        return '🟡 中等风险（中性区间）'
    elif rtsi_value >= 30:
        return '🟠 较高风险（弱势空头）'
    elif rtsi_value >= 20 and confidence >= 0.5:
        return '🔴 高风险（温和下跌）'
    elif rtsi_value < 20 and confidence >= 0.7:
        return '🔴 极高风险（强势下跌确认）'
    else:
        return '🔴 高风险'


def _calculate_score_change(scores: pd.Series, days: int) -> Optional[float]:
    """
    计算指定天数的评级分数变化
    
    参数:
        scores (pd.Series): 评级分数序列
        days (int): 计算天数
        
    返回:
        float: 分数变化，如果数据不足返回None
    """
    if len(scores) < days + 1:
        return None
    
    return float(scores.iloc[-1] - scores.iloc[-(days + 1)])


# 模块测试函数
def test_rtsi_calculator():
    """测试RTSI计算器功能"""
    print("测试 测试RTSI计算器...")
    
    # 构造测试数据
    test_ratings = pd.Series([
        '中空', '小空', '微空', '微多', '小多', '中多', '大多'
    ])
    
    # 测试单个计算
    result = calculate_rating_trend_strength_index(test_ratings)
    print(f"   测试结果: RTSI={result['rtsi']}, 趋势={result['trend']}")
    
    # 构造批量测试数据
    test_data = pd.DataFrame({
        '股票代码': ['000001', '000002', '000003'],
        '股票名称': ['测试股票A', '测试股票B', '测试股票C'],
        '行业': ['银行', '地产', '科技'],
        '20250601': ['中空', '微多', '大多'],
        '20250602': ['小空', '小多', '中多'],
        '20250603': ['微空', '中多', '小多'],
        '20250604': ['微多', '大多', '微多'],
        '20250605': ['小多', '中多', '微空']
    })
    
    # 测试批量计算
    batch_results = batch_calculate_rtsi(test_data)
    print(f"   批量测试: 处理 {len(batch_results)} 只股票")
    
    # 测试排名
    ranking = get_rtsi_ranking(batch_results, top_n=3)
    print(f"   排名测试: 前3名获取成功")
    
    # 测试统计
    stats = get_rtsi_statistics(batch_results)
    print(f"   统计测试: 成功率 {stats.get('success_rate', 0):.1f}%")
    
    print("成功 RTSI计算器测试完成")
    return True


if __name__ == "__main__":
    test_rtsi_calculator()


class RTSICalculator:
    """
    RTSI算法计算器类
    
    提供面向对象的RTSI计算接口，便于实例化和配置管理
    """
    
    def __init__(self, rating_map: Dict = None, min_data_points: int = 5):
        """
        初始化RTSI计算器
        
        参数:
            rating_map (dict): 评级映射表，默认使用RATING_SCORE_MAP
            min_data_points (int): 最少数据点要求，默认5个
        """
        self.rating_map = rating_map or RATING_SCORE_MAP
        self.min_data_points = min_data_points
        self.calculation_count = 0
    
    def calculate(self, stock_ratings: pd.Series) -> Dict[str, Union[float, str, int, None]]:
        """
        计算单只股票的RTSI指数
        
        参数:
            stock_ratings (pd.Series): 股票评级序列
            
        返回:
            dict: RTSI计算结果
        """
        self.calculation_count += 1
        return calculate_rating_trend_strength_index(stock_ratings)
    
    def batch_calculate(self, stock_data: pd.DataFrame) -> Dict[str, Dict]:
        """
        批量计算RTSI指数
        
        参数:
            stock_data (pd.DataFrame): 股票数据
            
        返回:
            dict: 批量计算结果
        """
        return batch_calculate_rtsi(stock_data)
    
    def get_ranking(self, rtsi_results: Dict[str, Dict], top_n: int = 50, 
                   trend_filter: Optional[str] = None) -> List[Tuple[str, str, float, str]]:
        """
        获取RTSI排名
        
        参数:
            rtsi_results (dict): RTSI计算结果
            top_n (int): 返回前N名
            trend_filter (str): 趋势过滤器
            
        返回:
            list: 排名结果
        """
        return get_rtsi_ranking(rtsi_results, top_n, trend_filter)
    
    def get_statistics(self, rtsi_results: Dict[str, Dict]) -> Dict[str, Union[int, float]]:
        """
        获取RTSI统计信息
        
        参数:
            rtsi_results (dict): RTSI计算结果
            
        返回:
            dict: 统计信息
        """
        return get_rtsi_statistics(rtsi_results)
    
    def reset_counter(self):
        """重置计算计数器"""
        self.calculation_count = 0
    
    def __str__(self):
        return f"RTSICalculator(calculations={self.calculation_count}, min_points={self.min_data_points})" 