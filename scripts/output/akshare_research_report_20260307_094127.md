# Akshare 实时数据接口研究报告

生成时间: 2026-03-07T09:40:41.798188

---

## 📊 概览

- **总函数数量**: 1078
- **实时数据接口**: 92
- **港股接口**: 52
- **美股接口**: 107
- **全球指数接口**: 133
- **期货接口**: 72
- **外汇接口**: 36
- **已测试API**: 16

---

## 🔴 实时数据接口

发现 92 个相关接口:

- `bond_spot_deal` - 中国外汇交易中心暨全国银行间同业拆借中心-市场数据-债券市场行情-现券市场成交行情
https://www.chinamoney.com.cn/chinese/
- `bond_spot_quote` - 中国外汇交易中心暨全国银行间同业拆借中心-市场数据-债券市场行情-现券市场做市报价
https://www.chinamoney.com.cn/chinese/
- `bond_zh_hs_cov_spot` - 新浪财经-债券-沪深可转债的实时行情数据; 大量抓取容易封IP
https://vip.stock.finance.sina.com.cn/mkt/#hskzz
- `bond_zh_hs_spot` - 新浪财经-债券-沪深债券-实时行情数据, 大量抓取容易封IP
https://vip.stock.finance.sina.com.cn/mkt/#hs_z
:
- `crypto_js_spot` - 主流加密货币的实时行情数据, 一次请求返回具体某一时刻行情数据
https://datacenter.jin10.com/reportType/dc_bitco
- `forex_spot_em` - 东方财富网-行情中心-外汇市场-所有汇率-实时行情数据
https://quote.eastmoney.com/center/gridlist.html#for
- `fund_etf_spot_em` - 东方财富-ETF 实时行情
https://quote.eastmoney.com/center/gridlist.html#fund_etf
:return:
- `fund_etf_spot_ths` - 同花顺理财-基金数据-每日净值-ETF-实时行情
https://fund.10jqka.com.cn/datacenter/jz/kfs/etf/
:para
- `fund_lof_spot_em` - 东方财富-LOF 实时行情
https://quote.eastmoney.com/center/gridlist.html#fund_lof
:return:
- `futures_delivery_czce` - 郑州商品交易所-月度交割查询
http://www.czce.com.cn/cn/jysj/ydjgcx/H770316index_1.htm
:param d
- `futures_delivery_dce` - 大连商品交易所-交割统计
http://www.dce.com.cn/dalianshangpin/xqsj/tjsj26/jgtj/jgsj/index.ht
- `futures_delivery_match_czce` - 郑州商品交易所-交割配对
http://www.czce.com.cn/cn/jysj/jgpd/H770308index_1.htm
:param date:
- `futures_delivery_match_dce` - 大连商品交易所-交割配对表
http://www.dce.com.cn/dalianshangpin/xqsj/tjsj26/jgtj/jgsj/index.h
- `futures_delivery_shfe` - 上海期货交易所-交割情况表
https://tsite.shfe.com.cn/statements/dataview.html?paramid=kx
注意: 
- `futures_foreign_commodity_realtime` - 新浪-外盘期货-行情数据
https://finance.sina.com.cn/money/future/hf.html
:param symbol: 通过调
- `futures_global_spot_em` - 东方财富网-行情中心-期货市场-国际期货
https://quote.eastmoney.com/center/gridlist.html#futures_gl
- `futures_spot_price` - 指定交易日大宗商品现货价格及相应基差
https://www.100ppi.com/sf/day-2017-09-12.html
:param date: 开始
- `futures_spot_price_daily` - 指定时间段内大宗商品现货价格及相应基差
https://www.100ppi.com/sf/
:param start_day: str 开始日期 format
- `futures_spot_price_previous` - 具体交易日大宗商品现货价格及相应基差
https://www.100ppi.com/sf/day-2017-09-12.html
:param date: 交易
- `futures_spot_stock` - 东方财富网-数据中心-现货与股票
https://data.eastmoney.com/ifdata/xhgp.html
:param symbol: choi
- `futures_spot_sys` - 生意社-商品与期货-现期图
https://www.100ppi.com/sf/792.html
:param symbol: 期货品种
:type symbo
- `futures_to_spot_czce` - 郑州商品交易所-期转现统计
http://www.czce.com.cn/cn/jysj/qzxtj/H770311index_1.htm
:param dat
- `futures_to_spot_dce` - 大连商品交易所-期转现
http://www.dce.com.cn/dalianshangpin/xqsj/tjsj26/jgtj/qzxcx/index.ht
- `futures_to_spot_shfe` - 上海期货交易所-期转现
https://tsite.shfe.com.cn/statements/dataview.html?paramid=kx
1、铜、铜(
- `futures_zh_realtime` - 期货品种当前时刻所有可交易的合约实时数据
https://vip.stock.finance.sina.com.cn/quotes_service/view/q
- `futures_zh_spot` - 期货的实时行情数据
https://vip.stock.finance.sina.com.cn/quotes_service/view/qihuohangqin
- `fx_spot_quote` - 中国外汇交易中心暨全国银行间同业拆借中心-市场数据-市场行情-外汇市场行情-人民币外汇即期报价
http://www.chinamoney.com.cn/chi
- `index_global_spot_em` - 东方财富网-行情中心-全球指数-实时行情数据
https://quote.eastmoney.com/center/gridlist.html#global_q
- `index_hog_spot_price` - 行情宝-生猪市场价格指数
https://hqb.nxin.com/pigindex/index.shtml
:return: 生猪市场价格指数
:rtype:
- `index_realtime_fund_sw` - 申万宏源研究-申万指数-指数发布-基金指数-实时行情
https://www.swsresearch.com/institute_sw/allIndex/rel
- ... 还有 62 个接口

---

## 🇭🇰 港股接口

发现 52 个相关接口:

- `fund_hk_fund_hist_em` - 东方财富网-天天基金网-基金数据-香港基金-历史净值明细(分红送配详情)
https://overseas.1234567.com.cn/f10/FundJz/
- `fund_hk_rank_em` - 东方财富网-数据中心-香港基金排行
https://overseas.1234567.com.cn/FundList
:return: 香港基金排行
:rtyp
- `get_qhkc_fund_bs` - 奇货可查-资金-净持仓分布
可获取数据的时间段为:"2016-10-10:2019-09-30"
:param url: 网址
:param date: 中文名
- `get_qhkc_fund_money_change` - 奇货可查-资金-成交额分布
可获取数据的时间段为:"2016-10-10:2019-09-30"
:param url: 网址
:param date: 中文名
- `get_qhkc_fund_position` - 奇货可查-资金-总持仓分布
可获取数据的时间段为:"2016-10-10:2019-09-30"
:param url: 网址
:param date: 中文名
- `get_qhkc_index` - 奇货可查-指数-指数详情
获得奇货可查的指数数据: '奇货黑链', '奇货商品', '奇货谷物', '奇货贵金属', '奇货饲料', '奇货软商品', '奇货化
- `get_qhkc_index_profit_loss` - 奇货可查-指数-盈亏详情
获得奇货可查的指数数据: '奇货黑链', '奇货商品', '奇货谷物', '奇货贵金属', '奇货饲料', '奇货软商品', '奇货化
- `get_qhkc_index_trend` - 奇货可查-指数-大资金动向
获得奇货可查的指数数据: '奇货黑链', '奇货商品', '奇货谷物', '奇货贵金属', '奇货饲料', '奇货软商品', '奇货
- `macro_china_hk_building_amount` - 东方财富-经济数据一览-中国香港-香港楼宇买卖合约成交金额
https://data.eastmoney.com/cjsj/foreign_8_6.html
:
- `macro_china_hk_building_volume` - 东方财富-经济数据一览-中国香港-香港楼宇买卖合约数量
https://data.eastmoney.com/cjsj/foreign_8_5.html
:re
- `macro_china_hk_cpi` - 东方财富-经济数据一览-中国香港-消费者物价指数
https://data.eastmoney.com/cjsj/foreign_8_0.html
:retur
- `macro_china_hk_cpi_ratio` - 东方财富-经济数据一览-中国香港-消费者物价指数年率
https://data.eastmoney.com/cjsj/foreign_8_1.html
:ret
- `macro_china_hk_gbp` - 东方财富-经济数据一览-中国香港-香港 GDP
https://data.eastmoney.com/cjsj/foreign_8_3.html
:return
- `macro_china_hk_gbp_ratio` - 东方财富-经济数据一览-中国香港-香港 GDP 同比
https://data.eastmoney.com/cjsj/foreign_8_4.html
:ret
- `macro_china_hk_market_info` - 香港同业拆借报告, 数据区间从 20170320-至今
https://datacenter.jin10.com/reportType/dc_hk_market
- `macro_china_hk_ppi` - 东方财富-经济数据一览-中国香港-香港制造业 PPI 年率
https://data.eastmoney.com/cjsj/foreign_8_8.html
:
- `macro_china_hk_rate_of_unemployment` - 东方财富-经济数据一览-中国香港-失业率
https://data.eastmoney.com/cjsj/foreign_8_2.html
:return: 失
- `macro_china_hk_trade_diff_ratio` - 东方财富-经济数据一览-中国香港-香港商品贸易差额年率
https://data.eastmoney.com/cjsj/foreign_8_7.html
:re
- `qhkc_tool_foreign` - 奇货可查-工具-外盘比价
实时更新数据, 暂不能查询历史数据
:param url: str 网址
:return: 外盘比价
:rtype: pandas.D
- `qhkc_tool_gdp` -   奇货可查-工具-各地区经济数据
  实时更新数据, 暂不能查询历史数据
  :param url:
  :return: pandas.DataFrame

- `stock_financial_hk_analysis_indicator_em` - 东方财富-港股-财务分析-主要指标
https://emweb.securities.eastmoney.com/PC_HKF10/NewFinancialAn
- `stock_financial_hk_report_em` - 东方财富-港股-财务报表-三大报表
https://emweb.securities.eastmoney.com/PC_HKF10/FinancialAnaly
- `stock_hk_company_profile_em` - 东方财富-港股-公司资料
https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/index.ht
- `stock_hk_daily` - 新浪财经-港股-个股的历史行情数据
https://stock.finance.sina.com.cn/hkstock/quotes/02912.html
:p
- `stock_hk_dividend_payout_em` - 东方财富-港股-核心必读-分红派息
https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/ind
- `stock_hk_famous_spot_em` - 东方财富网-行情中心-港股市场-知名港股
https://quote.eastmoney.com/center/gridlist.html#hk_wellkno
- `stock_hk_fhpx_detail_ths` - 同花顺-港股-分红派息
https://stockpage.10jqka.com.cn/HK0700/bonus/
:param symbol: 港股代码
:t
- `stock_hk_financial_indicator_em` - 东方财富-港股-核心必读-最新指标
https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/ind
- `stock_hk_ggt_components_em` - 东方财富网-行情中心-港股市场-港股通成份股
https://quote.eastmoney.com/center/gridlist.html#hk_compo
- `stock_hk_growth_comparison_em` - 东方财富-港股-行业对比-成长性对比
https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/in
- `stock_hk_gxl_lg` - 乐咕乐股-股息率-恒生指数股息率
https://legulegu.com/stockdata/market/hk/dv/hsi
:return: 恒生指数股息
- `stock_hk_hist` - 东方财富网-行情-港股-每日行情
https://quote.eastmoney.com/hk/08367.html
:param symbol: 港股-每日行
- `stock_hk_hist_min_em` - 东方财富网-行情-港股-每日分时行情
https://quote.eastmoney.com/hk/00948.html
:param symbol: 股票代码
- `stock_hk_hot_rank_detail_em` - 东方财富-个股人气榜-历史趋势
https://guba.eastmoney.com/rank/stock?code=HK_00700
:param symbo
- `stock_hk_hot_rank_detail_realtime_em` - 东方财富-个股人气榜-实时变动
https://guba.eastmoney.com/rank/stock?code=HK_00700
:param symbo
- `stock_hk_hot_rank_em` - 东方财富-个股人气榜-人气榜-港股市场
https://guba.eastmoney.com/rank/
:return: 人气榜
:rtype: pandas
- `stock_hk_hot_rank_latest_em` - 东方财富-个股人气榜-最新排名
https://guba.eastmoney.com/rank/stock?code=HK_00700
:param symbo
- `stock_hk_index_daily_em` - 东方财富网-港股-股票指数数据
https://quote.eastmoney.com/gb/zsHSTECF2L.html
:param symbol: 港股
- `stock_hk_index_daily_sina` - 新浪财经-港股指数-历史行情数据
https://stock.finance.sina.com.cn/hkstock/quotes/CES100.html
:p
- `stock_hk_index_spot_em` - 东方财富网-行情中心-港股-指数实时行情
https://quote.eastmoney.com/center/gridlist.html#hk_index
:
- `stock_hk_index_spot_sina` - 新浪财经-行情中心-港股指数
大量采集会被目标网站服务器封禁 IP, 如果被封禁 IP, 请 10 分钟后再试
https://vip.stock.financ
- `stock_hk_indicator_eniu` - 亿牛网-港股指标
https://eniu.com/gu/hk01093/roe
:param symbol: 港股代码
:type symbol: str
:
- `stock_hk_main_board_spot_em` - 东方财富网-港股-主板-实时行情
https://quote.eastmoney.com/center/gridlist.html#hk_mainboard
:
- `stock_hk_profit_forecast_et` - 经济通-公司资料-盈利预测
https://www.etnet.com.hk/www/sc/stocks/realtime/quote_profit.php?c
- `stock_hk_scale_comparison_em` - 东方财富-港股-行业对比-规模对比
https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/ind
- `stock_hk_security_profile_em` - 东方财富-港股-证券资料
https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/index.ht
- `stock_hk_spot` - 新浪财经-港股的所有港股的实时行情数据
https://vip.stock.finance.sina.com.cn/mkt/#qbgg_hk
:return: 
- `stock_hk_spot_em` - 东方财富网-港股-实时行情
https://quote.eastmoney.com/center/gridlist.html#hk_stocks
:return
- `stock_hk_valuation_baidu` - 百度股市通-港股-财务报表-估值数据
https://gushitong.baidu.com/stock/hk-06969
:param symbol: 股票代
- `stock_hk_valuation_comparison_em` - 东方财富-港股-行业对比-估值对比
https://emweb.securities.eastmoney.com/PC_HKF10/pages/home/ind
- `stock_hsgt_sh_hk_spot_em` - 东方财富网-行情中心-沪深港通-港股通(沪>港)-股票
https://quote.eastmoney.com/center/gridlist.html#hk_
- `stock_individual_basic_info_hk_xq` - 雪球-个股-公司概况-公司简介
https://xueqiu.com/S/00700
:param symbol: 证券代码
:type symbol: str

---

## 🇺🇸 美股接口

发现 107 个相关接口:

- `bond_gb_us_sina` - 新浪财经-债券-美国国债收益率行情数据
https://stock.finance.sina.com.cn/forex/globalbd/cn10yt.html
- `bond_zh_us_rate` - 东方财富网-数据中心-经济数据-中美国债收益率
https://data.eastmoney.com/cjsj/zmgzsyl.html
:param star
- `business_value_artist` - 艺恩-艺人-艺人商业价值
https://www.endata.com.cn/Marketing/Artist/business.html
:return: 艺
- `fund_portfolio_industry_allocation_em` - 天天基金网-基金档案-投资组合-行业配置
https://fundf10.eastmoney.com/hytz_000001.html
:param symbo
- `fund_report_industry_allocation_cninfo` - 巨潮资讯-数据中心-专题统计-基金报表-基金行业配置
https://webapi.cninfo.com.cn/#/thematicStatistics
:pa
- `futures_gfex_warehouse_receipt` - 广州期货交易所-行情数据-仓单日报
http://www.gfex.com.cn/gfex/cdrb/hqsj_tjsj.shtml
:param date: 
- `futures_shfe_warehouse_receipt` - 上海期货交易所指定交割仓库期货仓单日报
https://tsite.shfe.com.cn/statements/dataview.html?paramid=d
- `futures_spot_price_previous` - 具体交易日大宗商品现货价格及相应基差
https://www.100ppi.com/sf/day-2017-09-12.html
:param date: 交易
- `futures_warehouse_receipt_czce` - 郑州商品交易所-交易数据-仓单日报
http://www.czce.com.cn/cn/jysj/cdrb/H770310index_1.htm
:param 
- `futures_warehouse_receipt_dce` - 大连商品交易所-行情数据-统计数据-日统计-仓单日报
http://www.dce.com.cn/dce/channel/list/187.html
:para
- `get_us_stock_name` - u.s. stock's english name, chinese name and symbol
you should use symbol to get 
- `index_detail_hist_adjust_cni` - 国证指数-样本详情-历史调样
http://www.cnindex.com.cn/module/index-detail.html?act_menu=1&ind
- `index_us_stock_sina` - 新浪财经-美股指数行情
https://stock.finance.sina.com.cn/usstock/quotes/.IXIC.html
:param s
- `macro_australia_bank_rate` - 东方财富-经济数据-澳大利亚-央行公布利率决议
https://data.eastmoney.com/cjsj/foreign_5_6.html
:return
- `macro_australia_cpi_quarterly` - 东方财富-经济数据-澳大利亚-消费者物价指数季率
https://data.eastmoney.com/cjsj/foreign_5_4.html
:retur
- `macro_australia_cpi_yearly` - 东方财富-经济数据-澳大利亚-消费者物价指数年率
https://data.eastmoney.com/cjsj/foreign_5_5.html
:retur
- `macro_australia_ppi_quarterly` - 东方财富-经济数据-澳大利亚-生产者物价指数季率
https://data.eastmoney.com/cjsj/foreign_5_3.html
:retur
- `macro_australia_retail_rate_monthly` - 东方财富-经济数据-澳大利亚-零售销售月率
https://data.eastmoney.com/cjsj/foreign_5_0.html
:return: 
- `macro_australia_trade` - 东方财富-经济数据-澳大利亚-贸易帐
https://data.eastmoney.com/cjsj/foreign_5_1.html
:return: 贸易帐
- `macro_australia_unemployment_rate` - 东方财富-经济数据-澳大利亚-失业率
https://data.eastmoney.com/cjsj/foreign_5_2.html
:return: 失业率
- `macro_bank_australia_interest_rate` - 澳洲联储决议报告, 数据区间从 19800201-至今
https://datacenter.jin10.com/reportType/dc_australia
- `macro_bank_russia_interest_rate` - 俄罗斯利率决议报告, 数据区间从 20030601-至今
https://datacenter.jin10.com/reportType/dc_russia_i
- `macro_bank_usa_interest_rate` - 美联储利率决议报告, 数据区间从 19820927-至今
https://datacenter.jin10.com/reportType/dc_usa_inte
- `macro_canada_new_house_rate` - 东方财富-经济数据-加拿大-新屋开工
https://data.eastmoney.com/cjsj/foreign_7_0.html
:return: 新屋开
- `macro_china_industrial_production_yoy` - 中国规模以上工业增加值年率报告, 数据区间从19900301-至今
https://datacenter.jin10.com/reportType/dc_chi
- `macro_china_new_house_price` - 中国-新房价指数
https://data.eastmoney.com/cjsj/newhouse.html
:param city_first: 城市; 城市
- `macro_euro_industrial_production_mom` - 欧元区工业产出月率报告, 数据区间从19910301-至今
https://datacenter.jin10.com/reportType/dc_eurozon
- `macro_germany_trade_adjusted` - 东方财富-数据中心-经济数据一览-德国-贸易帐(季调后)
https://data.eastmoney.com/cjsj/foreign_1_3.html
:r
- `macro_usa_adp_employment` - 美国ADP就业人数报告, 数据区间从 20010601-至今
https://datacenter.jin10.com/reportType/dc_adp_no
- `macro_usa_api_crude_stock` - 美国 API 原油库存报告, 数据区间从 20120328-至今
https://datacenter.jin10.com/reportType/dc_usa_
- `macro_usa_building_permits` - 美国营建许可总数报告, 数据区间从 20080220-至今
https://datacenter.jin10.com/reportType/dc_usa_bui
- `macro_usa_business_inventories` - 美国商业库存月率报告, 数据区间从 19920301-至今
https://datacenter.jin10.com/reportType/dc_usa_bus
- `macro_usa_cb_consumer_confidence` - 金十数据中心-经济指标-美国-领先指标-美国谘商会消费者信心指数报告, 数据区间从 19700101-至今
https://datacenter.jin10.c
- `macro_usa_cftc_c_holding` - 美国商品期货交易委员会CFTC商品类非商业持仓报告, 数据区间从 19830107-至今
https://datacenter.jin10.com/report
- `macro_usa_cftc_merchant_currency_holding` - 美国商品期货交易委员会CFTC外汇类商业持仓报告, 数据区间从 19860115-至今
https://datacenter.jin10.com/reportT
- `macro_usa_cftc_merchant_goods_holding` - 美国商品期货交易委员会CFTC商品类商业持仓报告, 数据区间从 19860115-至今
https://datacenter.jin10.com/reportT
- `macro_usa_cftc_nc_holding` - 美国商品期货交易委员会CFTC外汇类非商业持仓报告, 数据区间从 19830107-至今
https://datacenter.jin10.com/report
- `macro_usa_cme_merchant_goods_holding` - CME-贵金属, 数据区间从 20180405-至今
https://datacenter.jin10.com/org
:return: CME-贵金属
:rt
- `macro_usa_core_cpi_monthly` - 美国核心 CPI 月率报告, 数据区间从 19700101-至今
https://datacenter.jin10.com/reportType/dc_usa_
- `macro_usa_core_pce_price` - 美国核心PCE物价指数年率报告, 数据区间从 19700101-至今
https://datacenter.jin10.com/reportType/dc_us
- `macro_usa_core_ppi` - 美国核心生产者物价指数(PPI)报告, 数据区间从20080318-至今
https://datacenter.jin10.com/reportType/dc_
- `macro_usa_cpi_monthly` - 美国 CPI 月率报告, 数据区间从 19700101-至今
https://datacenter.jin10.com/reportType/dc_usa_cp
- `macro_usa_cpi_yoy` - 东方财富-经济数据一览-美国-CPI年率, 数据区间从 2008-至今
https://data.eastmoney.com/cjsj/foreign_0_12
- `macro_usa_crude_inner` - 美国原油产量报告, 数据区间从 19830107-至今
https://datacenter.jin10.com/reportType/dc_eia_crude
- `macro_usa_current_account` - 美国经常帐报告, 数据区间从 20080317-至今
https://datacenter.jin10.com/reportType/dc_usa_curren
- `macro_usa_durable_goods_orders` - 美国耐用品订单月率报告, 数据区间从 20080227-至今
https://datacenter.jin10.com/reportType/dc_usa_du
- `macro_usa_eia_crude_rate` - 美国 EIA 原油库存报告, 数据区间从 19950801-至今
https://datacenter.jin10.com/reportType/dc_eia_
- `macro_usa_exist_home_sales` - 美国成屋销售总数年化报告, 数据区间从 19700101-至今
https://datacenter.jin10.com/reportType/dc_usa_e
- `macro_usa_export_price` - 美国出口价格指数报告, 数据区间从19890201-至今
https://datacenter.jin10.com/reportType/dc_usa_expo
- `macro_usa_factory_orders` - 美国工厂订单月率报告, 数据区间从 19920401-至今
https://datacenter.jin10.com/reportType/dc_usa_fac
- `macro_usa_gdp_monthly` - 金十数据-美国国内生产总值(GDP)报告, 数据区间从 20080228-至今
https://datacenter.jin10.com/reportType/
- `macro_usa_house_price_index` - 美国FHFA房价指数月率报告, 数据区间从 19910301-至今
https://datacenter.jin10.com/reportType/dc_usa
- `macro_usa_house_starts` - 美国新屋开工总数年化报告, 数据区间从 19700101-至今
https://datacenter.jin10.com/reportType/dc_usa_h
- `macro_usa_import_price` - 美国进口物价指数报告, 数据区间从19890201-至今
https://datacenter.jin10.com/reportType/dc_usa_impo
- `macro_usa_industrial_production` - 美国工业产出月率报告, 数据区间从 19700101-至今
https://datacenter.jin10.com/reportType/dc_usa_ind
- `macro_usa_initial_jobless` - 美国初请失业金人数报告, 数据区间从 19700101-至今
https://datacenter.jin10.com/reportType/dc_initia
- `macro_usa_ism_non_pmi` - 美国ISM非制造业PMI报告, 数据区间从 19970801-至今
https://datacenter.jin10.com/reportType/dc_usa
- `macro_usa_ism_pmi` - 美国 ISM 制造业 PMI 报告, 数据区间从 19700101-至今
https://datacenter.jin10.com/reportType/dc_
- `macro_usa_job_cuts` - 美国挑战者企业裁员人数报告, 数据区间从 19940201-至今
https://datacenter.jin10.com/reportType/dc_usa_
- `macro_usa_lmci` - 美联储劳动力市场状况指数报告, 数据区间从 20141006-至今
https://datacenter.jin10.com/reportType/dc_usa
- `macro_usa_michigan_consumer_sentiment` - 美国密歇根大学消费者信心指数初值报告, 数据区间从 19700301-至今
https://datacenter.jin10.com/reportType/dc
- `macro_usa_nahb_house_market_index` - 美国NAHB房产市场指数报告, 数据区间从 19850201-至今
https://datacenter.jin10.com/reportType/dc_usa
- `macro_usa_new_home_sales` - 美国新屋销售总数年化报告, 数据区间从 19700101-至今
https://datacenter.jin10.com/reportType/dc_usa_n
- `macro_usa_nfib_small_business` - 美国NFIB小型企业信心指数报告, 数据区间从 19750201-至今
https://datacenter.jin10.com/reportType/dc_u
- `macro_usa_non_farm` - 美国非农就业人数报告, 数据区间从19700102-至今
https://datacenter.jin10.com/reportType/dc_nonfarm_
- `macro_usa_pending_home_sales` - 美国成屋签约销售指数月率报告, 数据区间从 20010301-至今
https://datacenter.jin10.com/reportType/dc_usa
- `macro_usa_personal_spending` - 美国个人支出月率报告, 数据区间从19700101-至今
https://datacenter.jin10.com/reportType/dc_usa_pers
- `macro_usa_phs` - 东方财富-经济数据一览-美国-未决房屋销售月率
https://data.eastmoney.com/cjsj/foreign_0_5.html
:return
- `macro_usa_pmi` - 美国 Markit 制造业 PMI 初值报告, 数据区间从 20120601-至今
https://datacenter.jin10.com/reportTyp
- `macro_usa_ppi` - 美国生产者物价指数(PPI)报告, 数据区间从 20080226-至今
https://datacenter.jin10.com/reportType/dc_u
- `macro_usa_real_consumer_spending` - 美国实际个人消费支出季率初值报告, 数据区间从 20131107-至今
https://datacenter.jin10.com/reportType/dc_u
- `macro_usa_retail_sales` - 美国零售销售月率报告, 数据区间从 19920301-至今
https://datacenter.jin10.com/reportType/dc_usa_ret
- `macro_usa_rig_count` - 贝克休斯钻井报告, 数据区间从 20080317-至今
https://datacenter.jin10.com/reportType/dc_rig_count
- `macro_usa_services_pmi` - 美国Markit服务业PMI初值报告, 数据区间从 20120701-至今
https://datacenter.jin10.com/reportType/dc
- `macro_usa_spcs20` - 美国S&P/CS20座大城市房价指数年率报告, 数据区间从 20010201-至今
https://datacenter.jin10.com/reportTyp
- `macro_usa_trade_balance` - 美国贸易帐报告, 数据区间从 19700101-至今
https://datacenter.jin10.com/reportType/dc_usa_trade_
- `macro_usa_unemployment_rate` - 美国失业率报告, 数据区间从 19700101-至今
https://datacenter.jin10.com/reportType/dc_usa_unempl
- `news_trade_notify_suspend_baidu` - 百度股市通-交易提醒-停复牌
https://gushitong.baidu.com/calendar
:param date: 查询日期 (格式: YYYYM
- `stock_board_industry_cons_em` - 东方财富网-沪深板块-行业板块-板块成份
https://data.eastmoney.com/bkzj/BK1027.html
:param symbol: 
- `stock_board_industry_hist_em` - 东方财富网-沪深板块-行业板块-历史行情
https://quote.eastmoney.com/bk/90.BK1027.html
:param symbol
- `stock_board_industry_hist_min_em` - 东方财富网-沪深板块-行业板块-分时历史行情
https://quote.eastmoney.com/bk/90.BK1027.html
:param symb
- `stock_board_industry_index_ths` - 同花顺-板块-行业板块-指数数据
https://q.10jqka.com.cn/thshy/detail/code/881270/
:param start_
- `stock_board_industry_info_ths` - 同花顺-板块-行业板块-板块简介
http://q.10jqka.com.cn/gn/detail/code/301558/
:param symbol: 板块
- `stock_board_industry_name_em` - 东方财富网-沪深板块-行业板块-名称
https://quote.eastmoney.com/center/boardlist.html#industry_bo
- `stock_board_industry_name_ths` - 同花顺-板块-行业板块-行业
http://q.10jqka.com.cn/thshy/
:return: 所有行业板块的名称和链接
:rtype: panda
- `stock_board_industry_spot_em` - 东方财富网-沪深板块-行业板块-实时行情
https://quote.eastmoney.com/bk/90.BK1027.html
:param symbol
- `stock_board_industry_summary_ths` - 同花顺-数据中心-行业板块-同花顺行业一览表
https://q.10jqka.com.cn/thshy/
:return: 同花顺行业一览表
:rtype: 
- `stock_comment_detail_scrd_focus_em` - 东方财富网-数据中心-特色数据-千股千评-市场热度-用户关注指数
https://data.eastmoney.com/stockcomment/stock/6
- `stock_financial_us_analysis_indicator_em` - 东方财富-美股-财务分析-主要指标
https://emweb.eastmoney.com/PC_USF10/pages/index.html?code=TSL
- `stock_financial_us_report_em` - 东方财富-美股-财务分析-三大报表
https://emweb.eastmoney.com/PC_USF10/pages/index.html?code=TSL
- `stock_fund_flow_industry` - 同花顺-数据中心-资金流向-行业资金流
https://data.10jqka.com.cn/funds/hyzjl/#refCountId=data_55f1
- `stock_gpzy_industry_data_em` - 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例-行业数据
https://data.eastmoney.com/gpzy/industryData.
- `stock_hk_famous_spot_em` - 东方财富网-行情中心-港股市场-知名港股
https://quote.eastmoney.com/center/gridlist.html#hk_wellkno
- `stock_individual_basic_info_us_xq` - 雪球-个股-公司概况-公司简介
https://xueqiu.com/snowman/S/NVDA/detail#/GSJJ
:param symbol: 证券
- `stock_industry_category_cninfo` - 巨潮资讯-行业分类数据
https://webapi.cninfo.com.cn/#/apiDoc
查询 p_public0002 接口
:param symb
- `stock_industry_change_cninfo` - 巨潮资讯-上市公司行业归属的变动情况
https://webapi.cninfo.com.cn/#/apiDoc
查询 p_stock2110 接口
:para
- `stock_industry_clf_hist_sw` - 申万宏源研究-行业分类-全部行业分类
https://www.swsresearch.com/swindex/pdf/SwClass2021/StockClas
- `stock_industry_pe_ratio_cninfo` - 巨潮资讯-数据中心-行业分析-行业市盈率
http://webapi.cninfo.com.cn/#/thematicStatistics
:param sym
- `stock_us_daily` - 新浪财经-美股
https://finance.sina.com.cn/stock/usstock/sector.shtml
备注：
1. CIEN 新浪复权因
- `stock_us_famous_spot_em` - 东方财富网-行情中心-美股市场-知名美股
https://quote.eastmoney.com/center/gridlist.html#us_wellkno
- `stock_us_hist` - 东方财富网-行情-美股-每日行情
https://quote.eastmoney.com/us/ENTX.html#fullScreenChart
:param
- `stock_us_hist_min_em` - 东方财富网-行情首页-美股-每日分时行情
https://quote.eastmoney.com/us/ATER.html
:param symbol: 股票代
- `stock_us_pink_spot_em` - 东方财富网-行情中心-美股市场-粉单市场
https://quote.eastmoney.com/center/gridlist.html#us_pinkshe
- `stock_us_spot` - 新浪财经-所有美股的数据, 注意延迟 15 分钟
https://finance.sina.com.cn/stock/usstock/sector.shtml

- `stock_us_spot_em` - 东方财富网-美股-实时行情
https://quote.eastmoney.com/center/gridlist.html#us_stocks
:return
- `stock_us_valuation_baidu` - 百度股市通-美股-财务报表-估值数据
https://gushitong.baidu.com/stock/us-NVDA
:param symbol: 股票代码
- `stock_zt_pool_previous_em` - 东方财富网-行情中心-涨停板行情-昨日涨停股池
https://quote.eastmoney.com/ztb/detail#type=zrzt
:param 

---

## 🌍 全球指数接口

发现 133 个相关接口:

- `article_epu_index` - 经济政策不确定性指数
https://www.policyuncertainty.com/index.html
:param symbol: 指定的国家名称, 
- `bond_cb_index_jsl` - 首页-可转债-集思录可转债等权指数
https://www.jisilu.cn/web/data/cb/index
:return: 集思录可转债等权指数
:r
- `bond_composite_index_cbond` - 中国债券信息网-中债指数-中债指数族系-总指数-综合类指数-中债-综合指数
https://yield.chinabond.com.cn/cbweb-mn/in
- `bond_new_composite_index_cbond` - 中国债券信息网-中债指数-中债指数族系-总指数-综合类指数-中债-新综合指数
https://yield.chinabond.com.cn/cbweb-mn/i
- `drewry_wci_index` - Drewry 集装箱指数
https://infogram.com/world-container-index-1h17493095xl4zj
:param s
- `fund_info_index_em` - 东方财富网站-天天基金网-基金数据-基金信息-指数型
https://fund.eastmoney.com/trade/zs.html
:param symbo
- `futures_global_hist_em` - 东方财富网-行情中心-期货市场-国际期货-历史行情数据
https://quote.eastmoney.com/globalfuture/HG25J.html

- `futures_global_spot_em` - 东方财富网-行情中心-期货市场-国际期货
https://quote.eastmoney.com/center/gridlist.html#futures_gl
- `futures_index_ccidx` - 中证商品指数-商品指数-日频率
http://www.ccidx.com/index.html
:param symbol: choice of {"中证商品期
- `get_qhkc_index` - 奇货可查-指数-指数详情
获得奇货可查的指数数据: '奇货黑链', '奇货商品', '奇货谷物', '奇货贵金属', '奇货饲料', '奇货软商品', '奇货化
- `get_qhkc_index_profit_loss` - 奇货可查-指数-盈亏详情
获得奇货可查的指数数据: '奇货黑链', '奇货商品', '奇货谷物', '奇货贵金属', '奇货饲料', '奇货软商品', '奇货化
- `get_qhkc_index_trend` - 奇货可查-指数-大资金动向
获得奇货可查的指数数据: '奇货黑链', '奇货商品', '奇货谷物', '奇货贵金属', '奇货饲料', '奇货软商品', '奇货
- `index_ai_cx` - 财新数据-指数报告-AI策略指数
https://yun.ccxe.com.cn/indices/ai
:return: AI策略指数
:rtype: pand
- `index_all_cni` - 国证指数-最近交易日的所有指数
https://www.cnindex.com.cn/zh_indices/sese/index.html?act_menu=1
- `index_analysis_daily_sw` - 申万宏源研究-指数分析
https://www.swsresearch.com/institute_sw/allIndex/analysisIndex
:par
- `index_analysis_monthly_sw` - 申万宏源研究-指数分析-月报告
https://www.swsresearch.com/institute_sw/allIndex/analysisIndex

- `index_analysis_week_month_sw` - 申万宏源研究-周/月报表-日期序列
https://www.swsresearch.com/institute_sw/allIndex/analysisInde
- `index_analysis_weekly_sw` - 申万宏源研究-指数分析-周报告
https://www.swsresearch.com/institute_sw/allIndex/analysisIndex

- `index_awpr_cx` - 财新数据-指数报告-新经济入职工资溢价水平
https://yun.ccxe.com.cn/indices/nei
:return: 新经济入职工资溢价水平
:
- `index_bei_cx` - 财新数据-指数报告-基石经济指数
https://yun.ccxe.com.cn/indices/bei
:return: 基石经济指数
:rtype: pan
- `index_bi_cx` - 财新数据-指数报告-基础指数
https://yun.ccxe.com.cn/indices/dei
:return: 基础指数
:rtype: pandas.
- `index_bloomberg_billionaires` - Bloomberg Billionaires Index
https://www.bloomberg.com/billionaires/
:return: 彭博
- `index_bloomberg_billionaires_hist` - Bloomberg Billionaires Index
https://stats.areppim.com/stats/links_billionairexl
- `index_cci_cx` - 财新数据-指数报告-大宗商品指数
https://yun.ccxe.com.cn/indices/nei
:return: 大宗商品指数
:rtype: pan
- `index_ci_cx` - 财新数据-指数报告-资本投入指数
https://yun.ccxe.com.cn/indices/nei
:return: 资本投入指数
:rtype: pan
- `index_code_id_map_em` - 东方财富-股票和市场代码
https://quote.eastmoney.com/center/gridlist.html#hs_a_board
:return
- `index_component_sw` - 申万宏源研究-指数发布-指数详情-成分股
https://www.swsresearch.com/institute_sw/allIndex/releasedI
- `index_csindex_all` - 中证指数网站-指数列表
https://www.csindex.com.cn/#/indices/family/list?index_series=1
Note
- `index_dei_cx` - 财新数据-指数报告-数字经济指数
https://yun.ccxe.com.cn/indices/dei
:return: 数字经济指数
:rtype: pan
- `index_detail_cni` - 国证指数-样本详情-指定日期的样本成份
https://www.cnindex.com.cn/module/index-detail.html?act_menu
- `index_detail_hist_adjust_cni` - 国证指数-样本详情-历史调样
http://www.cnindex.com.cn/module/index-detail.html?act_menu=1&ind
- `index_detail_hist_cni` - 国证指数-样本详情-历史样本
https://www.cnindex.com.cn/module/index-detail.html?act_menu=1&in
- `index_eri` - 浙江省排污权交易指数
https://zs.zjpwq.net
:param symbol: choice of {"月度", "季度"}
:type symb
- `index_fi_cx` - 财新数据-指数报告-融合指数
https://yun.ccxe.com.cn/indices/dei
:return: 融合指数
:rtype: pandas.
- `index_global_hist_em` - 东方财富网-行情中心-全球指数-历史行情数据
https://quote.eastmoney.com/gb/zsUDI.html
:param symbol: 
- `index_global_hist_sina` - 新浪财经-行情中心-环球市场-历史行情
https://finance.sina.com.cn/stock/globalindex/quotes/UKX
:pa
- `index_global_name_table` - 新浪财经-行情中心-环球市场-名称代码映射表
https://finance.sina.com.cn/stock/globalindex/quotes/UKX

- `index_global_spot_em` - 东方财富网-行情中心-全球指数-实时行情数据
https://quote.eastmoney.com/center/gridlist.html#global_q
- `index_hist_cni` - 指数历史行情数据
http://www.cnindex.com.cn/module/index-detail.html?act_menu=1&indexCode
- `index_hist_fund_sw` - 申万宏源研究-申万指数-指数发布-基金指数-历史行情
https://www.swsresearch.com/institute_sw/allIndex/rel
- `index_hist_sw` - 申万宏源研究-指数发布-指数详情-指数历史数据
https://www.swsresearch.com/institute_sw/allIndex/releas
- `index_hog_spot_price` - 行情宝-生猪市场价格指数
https://hqb.nxin.com/pigindex/index.shtml
:return: 生猪市场价格指数
:rtype:
- `index_ii_cx` - 财新数据-指数报告-产业指数
https://yun.ccxe.com.cn/indices/dei
:return: 产业指数
:rtype: pandas.
- `index_inner_quote_sugar_msweet` - 沐甜科技数据中心-配额内进口糖估算指数
https://www.msweet.com.cn/mtkj/sjzx13/index.html
:return: 配额
- `index_kq_fashion` - 柯桥时尚指数
http://ss.kqindex.cn:9559/rinder_web_kqsszs/index/index_page.do
:param sy
- `index_kq_fz` - 中国柯桥纺织指数
http://www.kqindex.cn/flzs/jiage
:param symbol: choice of {'价格指数', '景气指
- `index_li_cx` - 财新数据-指数报告-劳动力投入指数
https://yun.ccxe.com.cn/indices/nei
:return: 劳动力投入指数
:rtype: p
- `index_min_sw` - 申万宏源研究-指数发布-指数详情-指数分时数据
https://www.swsresearch.com/institute_sw/allIndex/releas
- `index_neaw_cx` - 财新数据-指数报告-新经济行业入职平均工资水平
https://yun.ccxe.com.cn/indices/nei
:return: 新经济行业入职平均工资
- `index_neei_cx` - 财新数据-指数报告-新动能指数
https://yun.ccxe.com.cn/indices/neei
:return: 新动能指数
:rtype: pand
- `index_nei_cx` - 财新数据-指数报告-中国新经济指数
https://yun.ccxe.com.cn/indices/nei
:return: 中国新经济指数
:rtype: p
- `index_news_sentiment_scope` - 数库-A股新闻情绪指数
https://www.chinascope.com/reasearch.html
:return: A股新闻情绪指数
:rtype: 
- `index_option_1000index_min_qvix` - 中证1000股指 期权波动率指数 QVIX-分时
http://1.optbbs.com/s/vix.shtml?Index1000
:return: 中证10
- `index_option_1000index_qvix` - 中证1000股指 期权波动率指数 QVIX
http://1.optbbs.com/s/vix.shtml?Index1000
:return: 中证1000股
- `index_option_100etf_min_qvix` - 深证100ETF 期权波动率指数 QVIX-分时
http://1.optbbs.com/s/vix.shtml?100ETF
:return: 深证100ET
- `index_option_100etf_qvix` - 深证100ETF 期权波动率指数 QVIX
http://1.optbbs.com/s/vix.shtml?100ETF
:return: 深证100ETF 期
- `index_option_300etf_min_qvix` - 300 ETF 期权波动率指数 QVIX-分时
http://1.optbbs.com/s/vix.shtml?300ETF
:return: 300 ETF 
- `index_option_300etf_qvix` - 300 ETF 期权波动率指数 QVIX
http://1.optbbs.com/s/vix.shtml?300ETF
:return: 300 ETF 期权波
- `index_option_300index_min_qvix` - 中证300股指 期权波动率指数 QVIX-分时
http://1.optbbs.com/s/vix.shtml?Index
:return: 中证300股指 期
- `index_option_300index_qvix` - 中证300股指 期权波动率指数 QVIX
http://1.optbbs.com/s/vix.shtml?Index
:return: 中证300股指 期权波动
- `index_option_500etf_min_qvix` - 500 ETF 期权波动率指数 QVIX-分时
http://1.optbbs.com/s/vix.shtml?500ETF
:return: 500 ETF 
- `index_option_500etf_qvix` - 500 ETF 期权波动率指数 QVIX
http://1.optbbs.com/s/vix.shtml?500ETF
:return: 500 ETF 期权波
- `index_option_50etf_min_qvix` - 50 ETF 期权波动率指数 QVIX
http://1.optbbs.com/s/vix.shtml?50ETF
:return: 50 ETF 期权波动率指
- `index_option_50etf_qvix` - 50ETF 期权波动率指数 QVIX
http://1.optbbs.com/s/vix.shtml?50ETF
:return: 50ETF 期权波动率指数 
- `index_option_50index_min_qvix` - 上证50股指 期权波动率指数 QVIX-分时
http://1.optbbs.com/s/vix.shtml?50index
:return: 上证50股指 期
- `index_option_50index_qvix` - 上证50股指 期权波动率指数 QVIX
http://1.optbbs.com/s/vix.shtml?50index
:return: 上证50股指 期权波动
- `index_option_cyb_min_qvix` - 创业板 期权波动率指数 QVIX-分时
http://1.optbbs.com/s/vix.shtml?CYB
:return: 创业板 期权波动率指数 QVI
- `index_option_cyb_qvix` - 创业板 期权波动率指数 QVIX
http://1.optbbs.com/s/vix.shtml?CYB
:return: 创业板 期权波动率指数 QVIX
:
- `index_option_kcb_min_qvix` - 科创板 期权波动率指数 QVIX-分时
http://1.optbbs.com/s/vix.shtml?KCB
:return: 科创板 期权波动率指数 QVI
- `index_option_kcb_qvix` - 科创板 期权波动率指数 QVIX
http://1.optbbs.com/s/vix.shtml?KCB
:return: 科创板 期权波动率指数 QVIX
:
- `index_outer_quote_sugar_msweet` - 沐甜科技数据中心-配额外进口糖估算指数
https://www.msweet.com.cn/mtkj/sjzx13/index.html
:return: 配额
- `index_pmi_com_cx` - 财新数据-指数报告-财新中国 PMI-综合 PMI
https://yun.ccxe.com.cn/indices/pmi
:return: 财新中国 PMI-
- `index_pmi_man_cx` - 财新数据-指数报告-财新中国 PMI-制造业 PMI
https://yun.ccxe.com.cn/indices/pmi
:return: 财新中国 PMI
- `index_pmi_ser_cx` - 财新数据-指数报告-财新中国 PMI-服务业 PMI
https://yun.ccxe.com.cn/indices/pmi
:return: 财新中国 PMI
- `index_price_cflp` - 中国公路物流运价指数
http://index.0256.cn/expx.htm
:param symbol: choice of {"周指数", "月指数",
- `index_qli_cx` - 财新数据-指数报告-高质量因子
https://yun.ccxe.com.cn/indices/qli
:return: 高质量因子
:rtype: panda
- `index_realtime_fund_sw` - 申万宏源研究-申万指数-指数发布-基金指数-实时行情
https://www.swsresearch.com/institute_sw/allIndex/rel
- `index_realtime_sw` - 申万宏源研究-指数系列
https://www.swsresearch.com/institute_sw/allIndex/releasedIndex
:par
- `index_si_cx` - 财新数据-指数报告-溢出指数
https://yun.ccxe.com.cn/indices/dei
:return: 溢出指数
:rtype: pandas.
- `index_stock_cons` - 最新股票指数的成份股目录
https://vip.stock.finance.sina.com.cn/corp/view/vII_NewestComponent
- `index_stock_cons_csindex` - 中证指数网站-成份股目录
https://www.csindex.com.cn/zh-CN/indices/index-detail/000300
:param
- `index_stock_cons_sina` - 新浪新版股票指数成份页面, 目前该接口可获取指数数量较少
https://vip.stock.finance.sina.com.cn/mkt/#zhishu_0
- `index_stock_cons_weight_csindex` - 中证指数网站-样本权重
https://www.csindex.com.cn/zh-CN/indices/index-detail/000300
:param 
- `index_stock_info` - 聚宽-指数数据-指数列表
https://www.joinquant.com/data/dict/indexData
:return: 指数信息的数据框
:rt
- `index_sugar_msweet` - 沐甜科技数据中心-中国食糖指数
https://www.msweet.com.cn/mtkj/sjzx13/index.html
:return: 中国食糖指数
- `index_ti_cx` - 财新数据-指数报告-科技投入指数
https://yun.ccxe.com.cn/indices/nei
:return: 科技投入指数
:rtype: pan
- `index_us_stock_sina` - 新浪财经-美股指数行情
https://stock.finance.sina.com.cn/usstock/quotes/.IXIC.html
:param s
- `index_volume_cflp` - 中国公路物流运量指数
http://index.0256.cn/expx.htm
:param symbol: choice of {"月指数", "季度指数"
- `index_yw` - 义乌小商品指数
https://www.ywindex.com/Home/Product/index/
:param symbol: choice of {"周
- `index_zh_a_hist` - 东方财富网-中国股票指数-行情数据
https://quote.eastmoney.com/zz/2.000859.html
:param symbol: 指数
- `index_zh_a_hist_min_em` - 东方财富网-指数数据-每日分时行情
https://quote.eastmoney.com/center/hszs.html
:param symbol: 指数
- `macro_china_agricultural_index` - 农副指数
https://data.eastmoney.com/cjsj/hyzs_list_EMI00662543.html
:return: 农副指数
:r
- `macro_china_bdti_index` - 原油运输指数
https://data.eastmoney.com/cjsj/hyzs_list_EMI00107668.html
:return: 原油运输指
- `macro_china_bsi_index` - 超灵便型船运价指数
https://data.eastmoney.com/cjsj/hyzs_list_EMI00107667.html
:return: 超灵
- `macro_china_commodity_price_index` - 大宗商品价格
https://data.eastmoney.com/cjsj/hyzs_list_EMI00662535.html
:return: 大宗商品价
- `macro_china_construction_index` - 建材指数
https://data.eastmoney.com/cjsj/hyzs_list_EMI00662541.html
:return: 建材指数
:r
- `macro_china_construction_price_index` - 建材价格指数
https://data.eastmoney.com/cjsj/hyzs_list_EMI00237146.html
:return: 建材价格指
- `macro_china_energy_index` - 能源指数
https://data.eastmoney.com/cjsj/hyzs_list_EMI00662539.html
:return: 能源指数
:r
- `macro_china_enterprise_boom_index` - https://data.eastmoney.com/cjsj/qyjqzs.html
中国-企业景气及企业家信心指数
:return: 企业景气及企业家信心指
- `macro_china_freight_index` - 新浪财经-中国宏观经济数据-航贸运价指数
https://finance.sina.com.cn/mac/#industry-22-0-31-2
:return
- `macro_china_lpi_index` - 物流景气指数
https://data.eastmoney.com/cjsj/hyzs_list_EMI00352262.html
:return: 物流景气指
- `macro_china_retail_price_index` - 商品零售价格指数
https://finance.sina.com.cn/mac/#price-12-0-31-1
:return: 商品零售价格指数
:rty
- `macro_china_yw_electronic_index` - 义乌小商品指数-电子元器件
https://data.eastmoney.com/cjsj/hyzs_list_EMI00055551.html
:return
- `macro_global_sox_index` - 费城半导体指数
https://data.eastmoney.com/cjsj/hyzs_list_EMI00055562.html
:return: 费城半导
- `macro_usa_house_price_index` - 美国FHFA房价指数月率报告, 数据区间从 19910301-至今
https://datacenter.jin10.com/reportType/dc_usa
- `macro_usa_nahb_house_market_index` - 美国NAHB房产市场指数报告, 数据区间从 19850201-至今
https://datacenter.jin10.com/reportType/dc_usa
- `qdii_a_index_jsl` - 集思录-T+0 QDII-亚洲市场-亚洲指数
https://www.jisilu.cn/data/qdii/#qdiia
:return: T+0 QDII-
- `qdii_e_index_jsl` - 集思录-T+0 QDII-欧美市场-欧美指数
https://www.jisilu.cn/data/qdii/#qdiia
:return: T+0 QDII-
- `stock_board_concept_index_ths` - 同花顺-板块-概念板块-指数数据
https://q.10jqka.com.cn/gn/detail/code/301558/
:param start_dat
- `stock_board_industry_index_ths` - 同花顺-板块-行业板块-指数数据
https://q.10jqka.com.cn/thshy/detail/code/881270/
:param start_
- `stock_buffett_index_lg` - 乐估乐股-底部研究-巴菲特指标
https://legulegu.com/stockdata/marketcap-gdp
:return: 巴菲特指标
:rty
- `stock_hk_index_daily_em` - 东方财富网-港股-股票指数数据
https://quote.eastmoney.com/gb/zsHSTECF2L.html
:param symbol: 港股
- `stock_hk_index_daily_sina` - 新浪财经-港股指数-历史行情数据
https://stock.finance.sina.com.cn/hkstock/quotes/CES100.html
:p
- `stock_hk_index_spot_em` - 东方财富网-行情中心-港股-指数实时行情
https://quote.eastmoney.com/center/gridlist.html#hk_index
:
- `stock_hk_index_spot_sina` - 新浪财经-行情中心-港股指数
大量采集会被目标网站服务器封禁 IP, 如果被封禁 IP, 请 10 分钟后再试
https://vip.stock.financ
- `stock_index_pb_lg` - 乐咕乐股-指数市净率
https://legulegu.com/stockdata/sz50-pb
:param symbol: choice of {"上证5
- `stock_index_pe_lg` - 乐咕乐股-指数市盈率
https://legulegu.com/stockdata/sz50-ttm-lyr
:param symbol: choice of 
- `stock_info_global_cls` - 财联社-电报
https://www.cls.cn/telegraph
:param symbol: choice of {"全部", "重点"}
:type 
- `stock_info_global_em` - 东方财富-全球财经快讯
https://kuaixun.eastmoney.com/7_24.html
:return: 全球财经快讯
:rtype: pand
- `stock_info_global_futu` - 富途牛牛-快讯
https://news.futunn.com/main/live
:return: 快讯
:rtype: pandas.DataFrame
- `stock_info_global_sina` - 新浪财经-全球财经快讯
https://finance.sina.com.cn/7x24
:return: 全球财经快讯
:rtype: pandas.Data
- `stock_info_global_ths` - 同花顺财经-全球财经直播
https://news.10jqka.com.cn/realtimenews.html
:return: 全球财经直播
:rtype
- `stock_zh_index_daily` - 新浪财经-指数-历史行情数据, 大量抓取容易封 IP
https://finance.sina.com.cn/realstock/company/sh00090
- `stock_zh_index_daily_em` - 东方财富网-股票指数数据
https://quote.eastmoney.com/center/hszs.html
:param symbol: 带市场标识的指
- `stock_zh_index_daily_tx` - 腾讯证券-日频-股票或者指数历史数据
作为 ak.stock_zh_index_daily() 的补充, 因为在新浪中有部分指数数据缺失
注意都是: 前复权, 
- `stock_zh_index_hist_csindex` - 中证指数-具体指数-历史行情数据
P.S. 只有收盘价，正常情况下不应使用该接口，除非指数只有中证网站有
https://www.csindex.com.cn/
- `stock_zh_index_spot_em` - 东方财富网-行情中心-沪深京指数
https://quote.eastmoney.com/center/gridlist.html#index_sz
:para
- `stock_zh_index_spot_sina` - 新浪财经-行情中心首页-A股-分类-所有指数
大量采集会被目标网站服务器封禁 IP, 如果被封禁 IP, 请 10 分钟后再试
https://vip.stoc
- `stock_zh_index_value_csindex` - 中证指数-指数估值数据
https://www.csindex.com.cn/zh-CN/indices/index-detail/H30374#/indice
- `sw_index_first_info` - 乐咕乐股-申万一级-分类
https://legulegu.com/stockdata/sw-industry-overview#level1
:return:
- `sw_index_second_info` - 乐咕乐股-申万二级-分类
https://legulegu.com/stockdata/sw-industry-overview#level1
:return:
- `sw_index_third_cons` - 乐咕乐股-申万三级-行业成份
https://legulegu.com/stockdata/index-composition?industryCode=801
- `sw_index_third_info` - 乐咕乐股-申万三级-分类
https://legulegu.com/stockdata/sw-industry-overview#level1
:return:

---

## 📈 期货接口

发现 72 个相关接口:

- `amac_futures_info` - 中国证券投资基金业协会-信息公示-基金产品公示-期货公司集合资管产品公示
https://gs.amac.org.cn/amac-infodisc/res/po
- `futures_comex_inventory` - 东方财富网-数据中心-期货期权-COMEX库存数据
https://data.eastmoney.com/pmetal/comex/by.html
:param
- `futures_comm_info` - 九期网-期货手续费
https://www.9qihuo.com/qihuoshouxufei
:param symbol: choice of {"所有", 
- `futures_comm_js` - 金十财经-期货手续费
https://www.jin10.com/
:param date: 日期; 格式为 YYYYMMDD，例如 "20250213"
:t
- `futures_contract_detail` - 查询期货合约详情
https://finance.sina.com.cn/futures/quotes/V2101.shtml
:param symbol: 合
- `futures_contract_detail_em` - 查询期货合约详情
https://quote.eastmoney.com/qihuo/v2602F.html
:param symbol: 合约
:type s
- `futures_contract_info_cffex` - 中国金融期货交易所-数据-交易参数
http://www.gfex.com.cn/gfex/hyxx/ywcs.shtml
:param date: 查询日期

- `futures_contract_info_czce` - 郑州商品交易所-交易数据-参考数据
http://www.czce.com.cn/cn/jysj/cksj/H770322index_1.htm
:param 
- `futures_contract_info_dce` - 大连商品交易所-数据中心-业务数据-交易参数-合约信息
http://www.dce.com.cn/dce/channel/list/180.html
:ret
- `futures_contract_info_gfex` - 广州期货交易所-业务/服务-合约信息
http://www.gfex.com.cn/gfex/hyxx/ywcs.shtml
:return: 交易参数汇总查询
- `futures_contract_info_ine` - 上海国际能源交易中心-业务指南-交易参数汇总(期货)
https://www.ine.cn/bourseService/summary/?name=currin
- `futures_contract_info_shfe` - 上海期货交易所-交易所服务-业务数据-交易参数汇总查询
https://tsite.shfe.com.cn/bourseService/businessdata
- `futures_dce_position_rank` - 大连商品交易所-每日持仓排名-具体合约
http://www.dce.com.cn/dalianshangpin/xqsj/tjsj26/rtj/rcjccpm
- `futures_dce_position_rank_other` - 大连商品交易所-每日持仓排名-具体合约-补充
http://www.dce.com.cn/dalianshangpin/xqsj/tjsj26/rtj/rcjc
- `futures_delivery_czce` - 郑州商品交易所-月度交割查询
http://www.czce.com.cn/cn/jysj/ydjgcx/H770316index_1.htm
:param d
- `futures_delivery_dce` - 大连商品交易所-交割统计
http://www.dce.com.cn/dalianshangpin/xqsj/tjsj26/jgtj/jgsj/index.ht
- `futures_delivery_match_czce` - 郑州商品交易所-交割配对
http://www.czce.com.cn/cn/jysj/jgpd/H770308index_1.htm
:param date:
- `futures_delivery_match_dce` - 大连商品交易所-交割配对表
http://www.dce.com.cn/dalianshangpin/xqsj/tjsj26/jgtj/jgsj/index.h
- `futures_delivery_shfe` - 上海期货交易所-交割情况表
https://tsite.shfe.com.cn/statements/dataview.html?paramid=kx
注意: 
- `futures_display_main_sina` - 新浪主力连续合约品种一览表
https://finance.sina.com.cn/futuremarket/index.shtml
:return: 新浪主力
- `futures_fees_info` - openctp 期货交易费用参照表
http://openctp.cn/fees.html
:return: 期货交易费用参照表
:rtype: pandas.
- `futures_foreign_commodity_realtime` - 新浪-外盘期货-行情数据
https://finance.sina.com.cn/money/future/hf.html
:param symbol: 通过调
- `futures_foreign_commodity_subscribe_exchange_symbol` - 需要订阅的行情的代码
https://finance.sina.com.cn/money/future/hf.html
:return: 需要订阅的行情的代码

- `futures_foreign_detail` - foreign futures contract detail data
:param symbol: futures symbol, you can get 
- `futures_foreign_hist` - 外盘期货-历史行情数据-日频率
https://finance.sina.com.cn/money/future/hf.html
:param symbol: 
- `futures_gfex_position_rank` - 广州期货交易所-日成交持仓排名
http://www.gfex.com.cn/gfex/rcjccpm/hqsj_tjsj.shtml
:param date:
- `futures_gfex_warehouse_receipt` - 广州期货交易所-行情数据-仓单日报
http://www.gfex.com.cn/gfex/cdrb/hqsj_tjsj.shtml
:param date: 
- `futures_global_hist_em` - 东方财富网-行情中心-期货市场-国际期货-历史行情数据
https://quote.eastmoney.com/globalfuture/HG25J.html

- `futures_global_spot_em` - 东方财富网-行情中心-期货市场-国际期货
https://quote.eastmoney.com/center/gridlist.html#futures_gl
- `futures_hist_em` - 东方财富网-期货行情-行情数据
https://qhweb.eastmoney.com/quote
:param symbol: 期货代码
:type symb
- `futures_hist_table_em` - 东方财富网-期货行情-交易所品种对照表
https://quote.eastmoney.com/qihuo/al2505.html
:return: 交易所品种
- `futures_hog_core` - 玄田数据-核心数据
https://zhujia.zhuwang.com.cn
:param symbol: choice of {"外三元", "内三元", 
- `futures_hog_cost` - 玄田数据-成本维度
https://zhujia.zhuwang.com.cn
:param symbol: choice of {"玉米", "豆粕", "二
- `futures_hog_supply` - 玄田数据-供应维度
https://zhujia.zhuwang.com.cn
:param symbol: choice of {"猪肉批发价", "储备冻猪
- `futures_hold_pos_sina` - 新浪财经-期货-成交持仓
https://vip.stock.finance.sina.com.cn/q/view/vFutures_Positions_cjc
- `futures_hq_subscribe_exchange_symbol` - 将品种字典转化为 pandas.DataFrame
https://finance.sina.com.cn/money/future/hf.html
:retu
- `futures_index_ccidx` - 中证商品指数-商品指数-日频率
http://www.ccidx.com/index.html
:param symbol: choice of {"中证商品期
- `futures_inventory_99` - 99 期货网-大宗商品库存数据
https://www.99qh.com/data/stockIn?productId=12
:param symbol: 交易
- `futures_inventory_em` - 东方财富网-数据中心-期货库存数据
https://data.eastmoney.com/ifdata/kcsj.html
:param symbol: 支持品
- `futures_main_sina` - 新浪财经-期货-主力连续日数据
https://vip.stock.finance.sina.com.cn/quotes_service/view/qihuoh
- `futures_news_shmet` - 上海金属网-快讯
https://www.shmet.com/newsFlash/newsFlash.html?searchKeyword=
:param sy
- `futures_rule` - 国泰君安期货-交易日历数据表
https://www.gtjaqh.com/pc/calendar.html
:param date: 需要指定为交易日, 且是
- `futures_settle` - 期货交易所结算参数
:param date: 结算日期 format：YYYY-MM-DD 或 YYYYMMDD 或 datetime.date对象，默认为当前
- `futures_settle_cffex` - 中国金融期货交易所-结算参数
http://www.cffex.com.cn/jscs/
:param date: 结算参数日期 format：YYYY-MM-
- `futures_settle_czce` - 郑州商品交易所-结算参数
http://www.czce.com.cn/cn/jysj/jscs/H077003003index_1.htm
:param da
- `futures_settle_gfex` - 广州期货交易所-结算参数
http://www.gfex.com.cn/gfex/rjycs/ywcs.shtml
:param date: 结算参数日期 fo
- `futures_settle_ine` - 上海国际能源交易中心-结算参数
https://www.ine.cn/reports/businessdata/prmsummary/
:param date:
- `futures_settle_shfe` - 上海期货交易所-结算参数
https://www.shfe.com.cn/reports/tradedata/dailyandweeklydata/
:para
- `futures_settlement_price_sgx` - 新加坡交易所-衍生品-历史数据-历史结算价格
https://www.sgx.com/zh-hans/research-education/derivative
- `futures_shfe_warehouse_receipt` - 上海期货交易所指定交割仓库期货仓单日报
https://tsite.shfe.com.cn/statements/dataview.html?paramid=d
- `futures_spot_price` - 指定交易日大宗商品现货价格及相应基差
https://www.100ppi.com/sf/day-2017-09-12.html
:param date: 开始
- `futures_spot_price_daily` - 指定时间段内大宗商品现货价格及相应基差
https://www.100ppi.com/sf/
:param start_day: str 开始日期 format
- `futures_spot_price_previous` - 具体交易日大宗商品现货价格及相应基差
https://www.100ppi.com/sf/day-2017-09-12.html
:param date: 交易
- `futures_spot_stock` - 东方财富网-数据中心-现货与股票
https://data.eastmoney.com/ifdata/xhgp.html
:param symbol: choi
- `futures_spot_sys` - 生意社-商品与期货-现期图
https://www.100ppi.com/sf/792.html
:param symbol: 期货品种
:type symbo
- `futures_stock_shfe_js` - 金十财经-上海期货交易所指定交割仓库库存周报
https://datacenter.jin10.com/reportType/dc_shfe_weekly_st
- `futures_symbol_mark` - 期货的品种和代码映射
https://vip.stock.finance.sina.com.cn/quotes_service/view/js/qihuohan
- `futures_to_spot_czce` - 郑州商品交易所-期转现统计
http://www.czce.com.cn/cn/jysj/qzxtj/H770311index_1.htm
:param dat
- `futures_to_spot_dce` - 大连商品交易所-期转现
http://www.dce.com.cn/dalianshangpin/xqsj/tjsj26/jgtj/qzxcx/index.ht
- `futures_to_spot_shfe` - 上海期货交易所-期转现
https://tsite.shfe.com.cn/statements/dataview.html?paramid=kx
1、铜、铜(
- `futures_warehouse_receipt_czce` - 郑州商品交易所-交易数据-仓单日报
http://www.czce.com.cn/cn/jysj/cdrb/H770310index_1.htm
:param 
- `futures_warehouse_receipt_dce` - 大连商品交易所-行情数据-统计数据-日统计-仓单日报
http://www.dce.com.cn/dce/channel/list/187.html
:para
- `futures_zh_daily_sina` - 中国各品种期货日频率数据
https://finance.sina.com.cn/futures/quotes/V2105.shtml
:param symbo
- `futures_zh_minute_sina` - 中国各品种期货分钟频率数据
https://vip.stock.finance.sina.com.cn/quotes_service/view/qihuohan
- `futures_zh_realtime` - 期货品种当前时刻所有可交易的合约实时数据
https://vip.stock.finance.sina.com.cn/quotes_service/view/q
- `futures_zh_spot` - 期货的实时行情数据
https://vip.stock.finance.sina.com.cn/quotes_service/view/qihuohangqin
- `get_futures_daily` - 交易所日交易数据
:param start_date: 开始日期 format：YYYY-MM-DD 或 YYYYMMDD 或 datetime.date对象 
- `macro_china_commodity_price_index` - 大宗商品价格
https://data.eastmoney.com/cjsj/hyzs_list_EMI00662535.html
:return: 大宗商品价
- `option_commodity_contract_sina` - 当前可以查询的期权品种的合约日期
https://stock.finance.sina.com.cn/futures/view/optionsDP.php
:p
- `option_commodity_contract_table_sina` - 当前所有期权合约, 包括看涨期权合约和看跌期权合约
https://stock.finance.sina.com.cn/futures/view/options
- `option_commodity_hist_sina` - 合约历史行情-日频
https://stock.finance.sina.com.cn/futures/view/optionsDP.php
:param sy
- `rv_from_futures_zh_minute_sina` - 从新浪财经获取期货的分钟级历史行情数据,并进行数据清洗和格式化
https://vip.stock.finance.sina.com.cn/quotes_ser

---

## 💱 外汇接口

发现 36 个相关接口:

- `currency_boc_safe` - 人民币汇率中间价
https://www.safe.gov.cn/safe/rmbhlzjj/index.html
:return: 人民币汇率中间价
:rty
- `currency_boc_sina` - 新浪财经-中行人民币牌价历史数据查询
https://biz.finance.sina.com.cn/forex/forex.php?startdate=201
- `currency_convert` - currencies data from currencyscoop.com
https://currencyscoop.com/api-documentati
- `currency_currencies` - currencies data from currencyscoop.com
https://currencyscoop.com/api-documentati
- `currency_history` - Latest data from currencyscoop.com
https://currencyscoop.com/api-documentation
:
- `currency_latest` - Latest data from currencyscoop.com
https://currencyscoop.com/api-documentation
:
- `currency_pair_map` - 指定货币的所有可获取货币对的数据
https://cn.investing.com/currencies/cny-jmd
:param symbol: 指定货币
- `currency_time_series` - Time-series data from currencyscoop.com
P.S. need special authority
https://curr
- `forex_hist_em` - 东方财富网-行情中心-外汇市场-所有汇率-历史行情数据
https://quote.eastmoney.com/cnyrate/EURCNYC.html
:pa
- `forex_spot_em` - 东方财富网-行情中心-外汇市场-所有汇率-实时行情数据
https://quote.eastmoney.com/center/gridlist.html#for
- `fx_c_swap_cm` - 中国外汇交易中心暨全国银行间同业拆借中心-基准-外汇市场-外汇掉期曲线-外汇掉期 C-Swap 定盘曲线
https://www.chinamoney.org.
- `fx_pair_quote` - 中国外汇交易中心暨全国银行间同业拆借中心-市场数据-市场行情-债券市场行情-外币对即期报价
http://www.chinamoney.com.cn/chine
- `fx_quote_baidu` - 百度股市通-外汇-行情榜单
https://gushitong.baidu.com/top/foreign-rmb
:param symbol: choice 
- `fx_spot_quote` - 中国外汇交易中心暨全国银行间同业拆借中心-市场数据-市场行情-外汇市场行情-人民币外汇即期报价
http://www.chinamoney.com.cn/chi
- `fx_swap_quote` - 中国外汇交易中心暨全国银行间同业拆借中心-市场数据-市场行情-债券市场行情-人民币外汇远掉报价
https://www.chinamoney.com.cn/ch
- `macro_china_fx_gold` - 东方财富-外汇和黄金储备
https://data.eastmoney.com/cjsj/hjwh.html
:return: 外汇和黄金储备
:rtype: 
- `macro_china_fx_reserves_yearly` - 中国年度外汇储备数据, 数据区间从 20140115-至今
https://datacenter.jin10.com/reportType/dc_chinese
- `macro_china_international_tourism_fx` - 新浪财经-中国宏观经济数据-国际旅游外汇收入构成
https://finance.sina.com.cn/mac/#industry-15-0-31-3
:re
- `macro_fx_sentiment` - 金十数据-外汇-投机情绪报告
外汇投机情绪报告显示当前市场多空仓位比例，数据由8家交易平台提供，涵盖11个主要货币对和1个黄金品种。
报告内容: 品种: 澳元兑
- `macro_usa_cftc_merchant_currency_holding` - 美国商品期货交易委员会CFTC外汇类商业持仓报告, 数据区间从 19860115-至今
https://datacenter.jin10.com/reportT
- `stock_gdfx_free_holding_analyse_em` - 东方财富网-数据中心-股东分析-股东持股分析-十大流通股东
https://data.eastmoney.com/gdfx/HoldingAnalyse.htm
- `stock_gdfx_free_holding_change_em` - 东方财富网-数据中心-股东分析-股东持股变动统计-十大流通股东
https://data.eastmoney.com/gdfx/HoldingAnalyse.h
- `stock_gdfx_free_holding_detail_em` - 东方财富网-数据中心-股东分析-股东持股明细-十大流通股东
https://data.eastmoney.com/gdfx/HoldingAnalyse.htm
- `stock_gdfx_free_holding_statistics_em` - 东方财富网-数据中心-股东分析-股东持股统计-十大流通股东
https://data.eastmoney.com/gdfx/HoldingAnalyse.htm
- `stock_gdfx_free_holding_teamwork_em` - 东方财富网-数据中心-股东分析-股东协同-十大流通股东
https://data.eastmoney.com/gdfx/HoldingAnalyse.html

- `stock_gdfx_free_top_10_em` - 东方财富网-个股-十大流通股东
https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResea
- `stock_gdfx_holding_analyse_em` - 东方财富网-数据中心-股东分析-股东持股分析-十大股东
https://data.eastmoney.com/gdfx/HoldingAnalyse.html

- `stock_gdfx_holding_change_em` - 东方财富网-数据中心-股东分析-股东持股变动统计-十大股东
https://data.eastmoney.com/gdfx/HoldingAnalyse.htm
- `stock_gdfx_holding_detail_em` - 东方财富网-数据中心-股东分析-股东持股明细-十大股东
https://data.eastmoney.com/gdfx/HoldingAnalyse.html

- `stock_gdfx_holding_statistics_em` - 东方财富网-数据中心-股东分析-股东持股统计-十大股东
https://data.eastmoney.com/gdfx/HoldingAnalyse.html

- `stock_gdfx_holding_teamwork_em` - 东方财富网-数据中心-股东分析-股东协同-十大股东
https://data.eastmoney.com/gdfx/HoldingAnalyse.html
:p
- `stock_gdfx_top_10_em` - 东方财富网-个股-十大股东
https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearc
- `stock_sgt_reference_exchange_rate_sse` - 沪港通-港股通信息披露-参考汇率
https://www.sse.com.cn/services/hkexsc/disclo/ratios/
:return: 
- `stock_sgt_reference_exchange_rate_szse` - 深港通-港股通业务信息-参考汇率
https://www.szse.cn/szhk/hkbussiness/exchangerate/index.html
:r
- `stock_sgt_settlement_exchange_rate_sse` - 沪港通-港股通信息披露-结算汇兑
https://www.sse.com.cn/services/hkexsc/disclo/ratios/
:return: 
- `stock_sgt_settlement_exchange_rate_szse` - 深港通-港股通业务信息-结算汇率
https://www.szse.cn/szhk/hkbussiness/exchangerate/index.html
:r

---

## 🧪 API 测试结果

### FOREX

#### ✅ `currency_boc_safe`
- **状态**: success
- **响应时间**: 6675.61 ms
- **数据形状**: (7917, 26)
- **数据字段**: 日期, 美元, 欧元, 日元, 港元, 英镑, 澳元, 新西兰元, 新加坡元, 瑞士法郎
  - ... 还有 16 个字段
- **样例数据**:
```json
[
  {
    "日期": "1994-01-01",
    "美元": 870.0,
    "欧元": NaN,
    "日元": 7.78,
    "港元": 112.66,
    "英镑": NaN,
    "澳元": NaN,
    "新西兰元": NaN,
    "新加坡元": NaN,
    "瑞士法郎": NaN,
    "加元": NaN,
    "澳门元": NaN,
    "林吉特": NaN,
    "卢布": NaN,
    "兰特": NaN,
    "韩元": NaN,
    "迪拉姆": NaN,
    "里亚尔": NaN,
    "福林": NaN,
    "兹罗提": NaN,
    "丹麦克朗": NaN,
    "瑞典克朗": NaN,
    "挪威克朗": NaN,
    "里拉": NaN,
    "比索": NaN,
    "泰铢": NaN
  },
  {
    "日期": "1994-01-03",
    "美元": 870.0,
    "欧元": NaN,
    "日元": 7.78,
    "港元": 112.66,
    "英镑": NaN,
    "澳元": NaN,
    "新西兰元": NaN,
    "新加坡元": NaN,
    "瑞士法郎": NaN,
    "加元": NaN,
    "澳门元": NaN,
    "林吉特": NaN,
    "卢布": NaN,
    "兰特": NaN,
    "韩元": NaN,
    "迪拉姆": NaN,
    "里亚尔": NaN,
    "福林": NaN,
    "兹罗提": NaN,
    "丹麦克朗": NaN,
    "瑞典克朗": NaN,
    
```

#### ❌ `currency_latest`
- **状态**: failed
- **响应时间**: 0.00 ms
- **错误**: 'date'

### FUTURES

#### ⚠️ `futures_zh_spot`
- **状态**: skipped
- **响应时间**: 0.00 ms
- **错误**: 需要参数: futures_zh_spot() got an unexpected keyword argument 'subscribe_list'
- **备注**: 需要特定参数才能调用

#### ⚠️ `futures_foreign_commodity_realtime`
- **状态**: skipped
- **响应时间**: 0.00 ms
- **错误**: 需要参数: futures_foreign_commodity_realtime() missing 1 required positional argument: 'symbol'
- **备注**: 需要特定参数才能调用

### GLOBAL_INDEX

#### ⚠️ `index_global_hist_em`
- **状态**: skipped
- **响应时间**: 0.00 ms
- **错误**: 需要参数: index_global_hist_em() got an unexpected keyword argument 'period'
- **备注**: 需要特定参数才能调用

### HK

#### ❌ `stock_hk_ggt_components_em`
- **状态**: failed
- **响应时间**: 0.00 ms
- **错误**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

#### ❌ `stock_hk_spot_em`
- **状态**: failed
- **响应时间**: 0.00 ms
- **错误**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

#### ✅ `stock_hk_daily`
- **状态**: success
- **响应时间**: 268.89 ms
- **数据形状**: (5342, 6)
- **数据字段**: date, open, high, low, close, volume
- **样例数据**:
```json
[
  {
    "date": "2004-06-16",
    "open": 4.375,
    "high": 4.625,
    "low": 4.075,
    "close": 4.15,
    "volume": 439775000.0
  },
  {
    "date": "2004-06-17",
    "open": 4.15,
    "high": 4.375,
    "low": 4.125,
    "close": 4.225,
    "volume": 83801500.0
  },
  {
    "date": "2004-06-18",
    "open": 4.2,
    "high": 4.25,
    "low": 3.95,
    "close": 4.025,
    "volume": 36598000.0
  }
]
```

#### ❌ `stock_hk_hist`
- **状态**: failed
- **响应时间**: 0.00 ms
- **错误**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

### REALTIME

#### ❌ `stock_zh_a_spot_em`
- **状态**: failed
- **响应时间**: 0.00 ms
- **错误**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

#### ❌ `stock_zh_index_spot_em`
- **状态**: failed
- **响应时间**: 0.00 ms
- **错误**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

#### ❌ `bond_zh_hs_spot`
- **状态**: failed
- **响应时间**: 0.00 ms
- **错误**: No value to decode

#### ❌ `fund_etf_spot_em`
- **状态**: failed
- **响应时间**: 0.00 ms
- **错误**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

### US

#### ❌ `stock_us_spot_em`
- **状态**: failed
- **响应时间**: 0.00 ms
- **错误**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

#### ✅ `stock_us_daily`
- **状态**: success
- **响应时间**: 291.49 ms
- **数据形状**: (9900, 6)
- **数据字段**: date, open, high, low, close, volume
- **样例数据**:
```json
[
  {
    "date": "1984-09-07 00:00:00",
    "open": 26.5,
    "high": 26.87,
    "low": 26.25,
    "close": 26.5,
    "volume": 2981600.0
  },
  {
    "date": "1984-09-10 00:00:00",
    "open": 26.5,
    "high": 26.62,
    "low": 25.87,
    "close": 26.37,
    "volume": 2346400.0
  },
  {
    "date": "1984-09-11 00:00:00",
    "open": 26.62,
    "high": 27.37,
    "low": 26.62,
    "close": 26.87,
    "volume": 5444000.0
  }
]
```

#### ❌ `stock_us_hist`
- **状态**: failed
- **响应时间**: 0.00 ms
- **错误**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

---

## ⭐ 推荐接口

以下 3 个接口测试成功，推荐用于实时数据获取:

- `stock_hk_daily` (hk) - 268.9ms
- `stock_us_daily` (us) - 291.5ms
- `currency_boc_safe` (forex) - 6675.6ms

---

## 📋 附录：所有函数列表

<details>
<summary>点击展开 (1078 个函数)</summary>

```
air_city_table
air_quality_hebei
air_quality_hist
air_quality_rank
air_quality_watch_point
amac_aoin_info
amac_fund_abs
amac_fund_account_info
amac_fund_info
amac_fund_sub_info
amac_futures_info
amac_manager_cancelled_info
amac_manager_classify_info
amac_manager_info
amac_member_info
amac_member_sub_info
amac_person_bond_org_list
amac_person_fund_org_list
amac_securities_info
article_epu_index
article_ff_crr
article_oman_rv
article_oman_rv_short
article_rlab_rv
bank_fjcf_table_detail
bond_buy_back_hist_em
bond_cash_summary_sse
bond_cb_adj_logs_jsl
bond_cb_index_jsl
bond_cb_jsl
bond_cb_profile_sina
bond_cb_redeem_jsl
bond_cb_summary_sina
bond_china_close_return
bond_china_close_return_map
bond_china_yield
bond_composite_index_cbond
bond_corporate_issue_cninfo
bond_cov_comparison
bond_cov_issue_cninfo
bond_cov_stock_issue_cninfo
bond_deal_summary_sse
bond_debt_nafmii
bond_gb_us_sina
bond_gb_zh_sina
bond_info_cm
bond_info_cm_query
bond_info_detail_cm
bond_local_government_issue_cninfo
bond_new_composite_index_cbond
bond_sh_buy_back_em
bond_spot_deal
bond_spot_quote
bond_sz_buy_back_em
bond_treasure_issue_cninfo
bond_zh_cov
bond_zh_cov_info
bond_zh_cov_info_ths
bond_zh_cov_value_analysis
bond_zh_hs_cov_daily
bond_zh_hs_cov_min
bond_zh_hs_cov_pre_min
bond_zh_hs_cov_spot
bond_zh_hs_daily
bond_zh_hs_spot
bond_zh_us_rate
business_value_artist
car_market_cate_cpca
car_market_country_cpca
car_market_fuel_cpca
car_market_man_rank_cpca
car_market_segment_cpca
car_market_total_cpca
car_sale_rank_gasgoo
crypto_bitcoin_cme
crypto_bitcoin_hold_report
crypto_js_spot
currency_boc_safe
currency_boc_sina
currency_convert
currency_currencies
currency_history
currency_latest
currency_pair_map
currency_time_series
drewry_wci_index
energy_carbon_bj
energy_carbon_domestic
energy_carbon_eu
energy_carbon_gz
energy_carbon_hb
energy_carbon_sz
energy_oil_detail
energy_oil_hist
forbes_rank
forex_hist_em
forex_spot_em
fred_md
fred_qd
fund_announcement_dividend_em
fund_announcement_personnel_em
fund_announcement_report_em
fund_aum_em
fund_aum_hist_em
fund_aum_trend_em
fund_balance_position_lg
fund_cf_em
fund_etf_category_sina
fund_etf_category_ths
fund_etf_dividend_sina
fund_etf_fund_daily_em
fund_etf_fund_info_em
fund_etf_hist_em
fund_etf_hist_min_em
fund_etf_hist_sina
fund_etf_scale_sse
fund_etf_scale_szse
fund_etf_spot_em
fund_etf_spot_ths
fund_exchange_rank_em
fund_fee_em
fund_fh_em
fund_fh_rank_em
fund_financial_fund_daily_em
fund_financial_fund_info_em
fund_graded_fund_daily_em
fund_graded_fund_info_em
fund_hk_fund_hist_em
fund_hk_rank_em
fund_hold_structure_em
fund_individual_achievement_xq
fund_individual_analysis_xq
fund_individual_basic_info_xq
fund_individual_detail_hold_xq
fund_individual_detail_info_xq
fund_individual_profit_probability_xq
fund_info_index_em
fund_lcx_rank_em
fund_linghuo_position_lg
fund_lof_hist_em
fund_lof_hist_min_em
fund_lof_spot_em
fund_manager_em
fund_money_fund_daily_em
fund_money_fund_info_em
fund_money_rank_em
fund_name_em
fund_new_found_em
fund_new_found_ths
fund_open_fund_daily_em
fund_open_fund_info_em
fund_open_fund_rank_em
fund_overview_em
fund_portfolio_bond_hold_em
fund_portfolio_change_em
fund_portfolio_hold_em
fund_portfolio_industry_allocation_em
fund_purchase_em
fund_rating_all
fund_rating_ja
fund_rating_sh
fund_rating_zs
fund_report_asset_allocation_cninfo
fund_report_industry_allocation_cninfo
fund_report_stock_cninfo
fund_scale_change_em
fund_scale_close_sina
fund_scale_open_sina
fund_scale_structured_sina
fund_stock_position_lg
fund_value_estimation_em
futures_comex_inventory
futures_comm_info
futures_comm_js
futures_contract_detail
futures_contract_detail_em
futures_contract_info_cffex
futures_contract_info_czce
futures_contract_info_dce
futures_contract_info_gfex
futures_contract_info_ine
futures_contract_info_shfe
futures_dce_position_rank
futures_dce_position_rank_other
futures_delivery_czce
futures_delivery_dce
futures_delivery_match_czce
futures_delivery_match_dce
futures_delivery_shfe
futures_display_main_sina
futures_fees_info
futures_foreign_commodity_realtime
futures_foreign_commodity_subscribe_exchange_symbol
futures_foreign_detail
futures_foreign_hist
futures_gfex_position_rank
futures_gfex_warehouse_receipt
futures_global_hist_em
futures_global_spot_em
futures_hist_em
futures_hist_table_em
futures_hog_core
futures_hog_cost
futures_hog_supply
futures_hold_pos_sina
futures_hq_subscribe_exchange_symbol
futures_index_ccidx
futures_inventory_99
futures_inventory_em
futures_main_sina
futures_news_shmet
futures_rule
futures_settle
futures_settle_cffex
futures_settle_czce
futures_settle_gfex
futures_settle_ine
futures_settle_shfe
futures_settlement_price_sgx
futures_shfe_warehouse_receipt
futures_spot_price
futures_spot_price_daily
futures_spot_price_previous
futures_spot_stock
futures_spot_sys
futures_stock_shfe_js
futures_symbol_mark
futures_to_spot_czce
futures_to_spot_dce
futures_to_spot_shfe
futures_warehouse_receipt_czce
futures_warehouse_receipt_dce
futures_zh_daily_sina
futures_zh_minute_sina
futures_zh_realtime
futures_zh_spot
fx_c_swap_cm
fx_pair_quote
fx_quote_baidu
fx_spot_quote
fx_swap_quote
get_cffex_daily
get_cffex_rank_table
get_czce_daily
get_dce_daily
get_dce_rank_table
get_futures_daily
get_gfex_daily
get_ine_daily
get_qhkc_fund_bs
get_qhkc_fund_money_change
get_qhkc_fund_position
get_qhkc_index
get_qhkc_index_profit_loss
get_qhkc_index_trend
get_rank_sum
get_rank_sum_daily
get_rank_table_czce
get_receipt
get_roll_yield
get_roll_yield_bar
get_shfe_daily
get_shfe_rank_table
get_token
get_us_stock_name
hf_sp_500
hurun_rank
index_ai_cx
index_all_cni
index_analysis_daily_sw
index_analysis_monthly_sw
index_analysis_week_month_sw
index_analysis_weekly_sw
index_awpr_cx
index_bei_cx
index_bi_cx
index_bloomberg_billionaires
index_bloomberg_billionaires_hist
index_cci_cx
index_ci_cx
index_code_id_map_em
index_component_sw
index_csindex_all
index_dei_cx
index_detail_cni
index_detail_hist_adjust_cni
index_detail_hist_cni
index_eri
index_fi_cx
index_global_hist_em
index_global_hist_sina
index_global_name_table
index_global_spot_em
index_hist_cni
index_hist_fund_sw
index_hist_sw
index_hog_spot_price
index_ii_cx
index_inner_quote_sugar_msweet
index_kq_fashion
index_kq_fz
index_li_cx
index_min_sw
index_neaw_cx
index_neei_cx
index_nei_cx
index_news_sentiment_scope
index_option_1000index_min_qvix
index_option_1000index_qvix
index_option_100etf_min_qvix
index_option_100etf_qvix
index_option_300etf_min_qvix
index_option_300etf_qvix
index_option_300index_min_qvix
index_option_300index_qvix
index_option_500etf_min_qvix
index_option_500etf_qvix
index_option_50etf_min_qvix
index_option_50etf_qvix
index_option_50index_min_qvix
index_option_50index_qvix
index_option_cyb_min_qvix
index_option_cyb_qvix
index_option_kcb_min_qvix
index_option_kcb_qvix
index_outer_quote_sugar_msweet
index_pmi_com_cx
index_pmi_man_cx
index_pmi_ser_cx
index_price_cflp
index_qli_cx
index_realtime_fund_sw
index_realtime_sw
index_si_cx
index_stock_cons
index_stock_cons_csindex
index_stock_cons_sina
index_stock_cons_weight_csindex
index_stock_info
index_sugar_msweet
index_ti_cx
index_us_stock_sina
index_volume_cflp
index_yw
index_zh_a_hist
index_zh_a_hist_min_em
macro_australia_bank_rate
macro_australia_cpi_quarterly
macro_australia_cpi_yearly
macro_australia_ppi_quarterly
macro_australia_retail_rate_monthly
macro_australia_trade
macro_australia_unemployment_rate
macro_bank_australia_interest_rate
macro_bank_brazil_interest_rate
macro_bank_china_interest_rate
macro_bank_english_interest_rate
macro_bank_euro_interest_rate
macro_bank_india_interest_rate
macro_bank_japan_interest_rate
macro_bank_newzealand_interest_rate
macro_bank_russia_interest_rate
macro_bank_switzerland_interest_rate
macro_bank_usa_interest_rate
macro_canada_bank_rate
macro_canada_core_cpi_monthly
macro_canada_core_cpi_yearly
macro_canada_cpi_monthly
macro_canada_cpi_yearly
macro_canada_gdp_monthly
macro_canada_new_house_rate
macro_canada_retail_rate_monthly
macro_canada_trade
macro_canada_unemployment_rate
macro_china_agricultural_index
macro_china_agricultural_product
macro_china_au_report
macro_china_bank_financing
macro_china_bdti_index
macro_china_bond_public
macro_china_bsi_index
macro_china_central_bank_balance
macro_china_commodity_price_index
macro_china_construction_index
macro_china_construction_price_index
macro_china_consumer_goods_retail
macro_china_cpi
macro_china_cpi_monthly
macro_china_cpi_yearly
macro_china_cx_pmi_yearly
macro_china_cx_services_pmi_yearly
macro_china_czsr
macro_china_daily_energy
macro_china_energy_index
macro_china_enterprise_boom_index
macro_china_exports_yoy
macro_china_fdi
macro_china_foreign_exchange_gold
macro_china_freight_index
macro_china_fx_gold
macro_china_fx_reserves_yearly
macro_china_gdp
macro_china_gdp_yearly
macro_china_gdzctz
macro_china_gyzjz
macro_china_hgjck
macro_china_hk_building_amount
macro_china_hk_building_volume
macro_china_hk_cpi
macro_china_hk_cpi_ratio
macro_china_hk_gbp
macro_china_hk_gbp_ratio
macro_china_hk_market_info
macro_china_hk_ppi
macro_china_hk_rate_of_unemployment
macro_china_hk_trade_diff_ratio
macro_china_imports_yoy
macro_china_industrial_production_yoy
macro_china_insurance
macro_china_insurance_income
macro_china_international_tourism_fx
macro_china_lpi_index
macro_china_lpr
macro_china_m2_yearly
macro_china_market_margin_sh
macro_china_market_margin_sz
macro_china_mobile_number
macro_china_money_supply
macro_china_national_tax_receipts
macro_china_nbs_nation
macro_china_nbs_region
macro_china_new_financial_credit
macro_china_new_house_price
macro_china_non_man_pmi
macro_china_passenger_load_factor
macro_china_pmi
macro_china_pmi_yearly
macro_china_postal_telecommunicational
macro_china_ppi
macro_china_ppi_yearly
macro_china_qyspjg
macro_china_real_estate
macro_china_reserve_requirement_ratio
macro_china_retail_price_index
macro_china_rmb
macro_china_shibor_all
macro_china_shrzgm
macro_china_society_electricity
macro_china_society_traffic_volume
macro_china_stock_market_cap
macro_china_supply_of_money
macro_china_swap_rate
macro_china_trade_balance
macro_china_urban_unemployment
macro_china_vegetable_basket
macro_china_wbck
macro_china_whxd
macro_china_xfzxx
macro_china_yw_electronic_index
macro_cnbs
macro_cons_gold
macro_cons_opec_month
macro_cons_silver
macro_euro_cpi_mom
macro_euro_cpi_yoy
macro_euro_current_account_mom
macro_euro_employment_change_qoq
macro_euro_gdp_yoy
macro_euro_industrial_production_mom
macro_euro_lme_holding
macro_euro_lme_stock
macro_euro_manufacturing_pmi
macro_euro_ppi_mom
macro_euro_retail_sales_mom
macro_euro_sentix_investor_confidence
macro_euro_services_pmi
macro_euro_trade_balance
macro_euro_unemployment_rate_mom
macro_euro_zew_economic_sentiment
macro_fx_sentiment
macro_germany_cpi_monthly
macro_germany_cpi_yearly
macro_germany_gdp
macro_germany_ifo
macro_germany_retail_sale_monthly
macro_germany_retail_sale_yearly
macro_germany_trade_adjusted
macro_germany_zew
macro_global_sox_index
macro_info_ws
macro_japan_bank_rate
macro_japan_core_cpi_yearly
macro_japan_cpi_yearly
macro_japan_head_indicator
macro_japan_unemployment_rate
macro_rmb_deposit
macro_rmb_loan
macro_shipping_bci
macro_shipping_bcti
macro_shipping_bdi
macro_shipping_bpi
macro_stock_finance
macro_swiss_cpi_yearly
macro_swiss_gbd_bank_rate
macro_swiss_gbd_yearly
macro_swiss_gdp_quarterly
macro_swiss_svme
macro_swiss_trade
macro_uk_bank_rate
macro_uk_core_cpi_monthly
macro_uk_core_cpi_yearly
macro_uk_cpi_monthly
macro_uk_cpi_yearly
macro_uk_gdp_quarterly
macro_uk_gdp_yearly
macro_uk_halifax_monthly
macro_uk_halifax_yearly
macro_uk_retail_monthly
macro_uk_retail_yearly
macro_uk_rightmove_monthly
macro_uk_rightmove_yearly
macro_uk_trade
macro_uk_unemployment_rate
macro_usa_adp_employment
macro_usa_api_crude_stock
macro_usa_building_permits
macro_usa_business_inventories
macro_usa_cb_consumer_confidence
macro_usa_cftc_c_holding
macro_usa_cftc_merchant_currency_holding
macro_usa_cftc_merchant_goods_holding
macro_usa_cftc_nc_holding
macro_usa_cme_merchant_goods_holding
macro_usa_core_cpi_monthly
macro_usa_core_pce_price
macro_usa_core_ppi
macro_usa_cpi_monthly
macro_usa_cpi_yoy
macro_usa_crude_inner
macro_usa_current_account
macro_usa_durable_goods_orders
macro_usa_eia_crude_rate
macro_usa_exist_home_sales
macro_usa_export_price
macro_usa_factory_orders
macro_usa_gdp_monthly
macro_usa_house_price_index
macro_usa_house_starts
macro_usa_import_price
macro_usa_industrial_production
macro_usa_initial_jobless
macro_usa_ism_non_pmi
macro_usa_ism_pmi
macro_usa_job_cuts
macro_usa_lmci
macro_usa_michigan_consumer_sentiment
macro_usa_nahb_house_market_index
macro_usa_new_home_sales
macro_usa_nfib_small_business
macro_usa_non_farm
macro_usa_pending_home_sales
macro_usa_personal_spending
macro_usa_phs
macro_usa_pmi
macro_usa_ppi
macro_usa_real_consumer_spending
macro_usa_retail_sales
macro_usa_rig_count
macro_usa_services_pmi
macro_usa_spcs20
macro_usa_trade_balance
macro_usa_unemployment_rate
match_main_contract
migration_area_baidu
migration_scale_baidu
movie_boxoffice_cinema_daily
movie_boxoffice_cinema_weekly
movie_boxoffice_daily
movie_boxoffice_monthly
movie_boxoffice_realtime
movie_boxoffice_weekly
movie_boxoffice_yearly
movie_boxoffice_yearly_first_week
news_cctv
news_economic_baidu
news_report_time_baidu
news_trade_notify_dividend_baidu
news_trade_notify_suspend_baidu
nlp_answer
nlp_ownthink
online_value_artist
option_cffex_hs300_daily_sina
option_cffex_hs300_list_sina
option_cffex_hs300_spot_sina
option_cffex_sz50_daily_sina
option_cffex_sz50_list_sina
option_cffex_sz50_spot_sina
option_cffex_zz1000_daily_sina
option_cffex_zz1000_list_sina
option_cffex_zz1000_spot_sina
option_comm_info
option_comm_symbol
option_commodity_contract_sina
option_commodity_contract_table_sina
option_commodity_hist_sina
option_contract_info_ctp
option_current_day_sse
option_current_day_szse
option_current_em
option_daily_stats_sse
option_daily_stats_szse
option_finance_board
option_finance_minute_sina
option_finance_sse_underlying
option_hist_czce
option_hist_dce
option_hist_gfex
option_hist_shfe
option_hist_yearly_czce
option_lhb_em
option_margin
option_margin_symbol
option_minute_em
option_premium_analysis_em
option_risk_analysis_em
option_risk_indicator_sse
option_sse_codes_sina
option_sse_daily_sina
option_sse_expire_day_sina
option_sse_greeks_sina
option_sse_list_sina
option_sse_minute_sina
option_sse_spot_price_sina
option_sse_underlying_spot_price_sina
option_value_analysis_em
option_vol_gfex
option_vol_shfe
pro_api
qdii_a_index_jsl
qdii_e_comm_jsl
qdii_e_index_jsl
qhkc_tool_foreign
qhkc_tool_gdp
rate_interbank
reits_hist_em
reits_hist_min_em
reits_realtime_em
repo_rate_hist
repo_rate_query
rv_from_futures_zh_minute_sina
rv_from_stock_zh_a_hist_min_em
set_token
spot_corn_price_soozhu
spot_golden_benchmark_sge
spot_goods
spot_hist_sge
spot_hog_crossbred_soozhu
spot_hog_lean_price_soozhu
spot_hog_soozhu
spot_hog_three_way_soozhu
spot_hog_year_trend_soozhu
spot_mixed_feed_soozhu
spot_price_qh
spot_price_table_qh
spot_quotations_sge
spot_silver_benchmark_sge
spot_soybean_price_soozhu
spot_symbol_table_sge
stock_a_all_pb
stock_a_below_net_asset_statistics
stock_a_code_to_symbol
stock_a_congestion_lg
stock_a_gxl_lg
stock_a_high_low_statistics
stock_a_ttm_lyr
stock_account_statistics_em
stock_add_stock
stock_allotment_cninfo
stock_analyst_detail_em
stock_analyst_rank_em
stock_balance_sheet_by_report_delisted_em
stock_balance_sheet_by_report_em
stock_balance_sheet_by_yearly_em
stock_bid_ask_em
stock_bj_a_spot_em
stock_board_change_em
stock_board_concept_cons_em
stock_board_concept_hist_em
stock_board_concept_hist_min_em
stock_board_concept_index_ths
stock_board_concept_info_ths
stock_board_concept_name_em
stock_board_concept_name_ths
stock_board_concept_spot_em
stock_board_concept_summary_ths
stock_board_industry_cons_em
stock_board_industry_hist_em
stock_board_industry_hist_min_em
stock_board_industry_index_ths
stock_board_industry_info_ths
stock_board_industry_name_em
stock_board_industry_name_ths
stock_board_industry_spot_em
stock_board_industry_summary_ths
stock_buffett_index_lg
stock_cash_flow_sheet_by_quarterly_em
stock_cash_flow_sheet_by_report_delisted_em
stock_cash_flow_sheet_by_report_em
stock_cash_flow_sheet_by_yearly_em
stock_cg_equity_mortgage_cninfo
stock_cg_guarantee_cninfo
stock_cg_lawsuit_cninfo
stock_changes_em
stock_circulate_stock_holder
stock_classify_sina
stock_comment_detail_scrd_desire_em
stock_comment_detail_scrd_focus_em
stock_comment_detail_zhpj_lspf_em
stock_comment_detail_zlkp_jgcyd_em
stock_comment_em
stock_concept_cons_futu
stock_concept_fund_flow_hist
stock_cy_a_spot_em
stock_cyq_em
stock_dividend_cninfo
stock_dxsyl_em
stock_dzjy_hygtj
stock_dzjy_hyyybtj
stock_dzjy_mrmx
stock_dzjy_mrtj
stock_dzjy_sctj
stock_dzjy_yybph
stock_ebs_lg
stock_esg_hz_sina
stock_esg_msci_sina
stock_esg_rate_sina
stock_esg_rft_sina
stock_esg_zd_sina
stock_fhps_detail_em
stock_fhps_detail_ths
stock_fhps_em
stock_financial_abstract
stock_financial_abstract_new_ths
stock_financial_abstract_ths
stock_financial_analysis_indicator
stock_financial_analysis_indicator_em
stock_financial_benefit_new_ths
stock_financial_benefit_ths
stock_financial_cash_new_ths
stock_financial_cash_ths
stock_financial_debt_new_ths
stock_financial_debt_ths
stock_financial_hk_analysis_indicator_em
stock_financial_hk_report_em
stock_financial_report_sina
stock_financial_us_analysis_indicator_em
stock_financial_us_report_em
stock_fund_flow_big_deal
stock_fund_flow_concept
stock_fund_flow_individual
stock_fund_flow_industry
stock_fund_stock_holder
stock_gddh_em
stock_gdfx_free_holding_analyse_em
stock_gdfx_free_holding_change_em
stock_gdfx_free_holding_detail_em
stock_gdfx_free_holding_statistics_em
stock_gdfx_free_holding_teamwork_em
stock_gdfx_free_top_10_em
stock_gdfx_holding_analyse_em
stock_gdfx_holding_change_em
stock_gdfx_holding_detail_em
stock_gdfx_holding_statistics_em
stock_gdfx_holding_teamwork_em
stock_gdfx_top_10_em
stock_ggcg_em
stock_gpzy_distribute_statistics_bank_em
stock_gpzy_distribute_statistics_company_em
stock_gpzy_industry_data_em
stock_gpzy_pledge_ratio_detail_em
stock_gpzy_pledge_ratio_em
stock_gpzy_profile_em
stock_gsrl_gsdt_em
stock_history_dividend
stock_history_dividend_detail
stock_hk_company_profile_em
stock_hk_daily
stock_hk_dividend_payout_em
stock_hk_famous_spot_em
stock_hk_fhpx_detail_ths
stock_hk_financial_indicator_em
stock_hk_ggt_components_em
stock_hk_growth_comparison_em
stock_hk_gxl_lg
stock_hk_hist
stock_hk_hist_min_em
stock_hk_hot_rank_detail_em
stock_hk_hot_rank_detail_realtime_em
stock_hk_hot_rank_em
stock_hk_hot_rank_latest_em
stock_hk_index_daily_em
stock_hk_index_daily_sina
stock_hk_index_spot_em
stock_hk_index_spot_sina
stock_hk_indicator_eniu
stock_hk_main_board_spot_em
stock_hk_profit_forecast_et
stock_hk_scale_comparison_em
stock_hk_security_profile_em
stock_hk_spot
stock_hk_spot_em
stock_hk_valuation_baidu
stock_hk_valuation_comparison_em
stock_hold_change_cninfo
stock_hold_control_cninfo
stock_hold_management_detail_cninfo
stock_hold_management_detail_em
stock_hold_management_person_em
stock_hold_num_cninfo
stock_hot_deal_xq
stock_hot_follow_xq
stock_hot_keyword_em
stock_hot_rank_detail_em
stock_hot_rank_detail_realtime_em
stock_hot_rank_em
stock_hot_rank_latest_em
stock_hot_rank_relate_em
stock_hot_search_baidu
stock_hot_tweet_xq
stock_hot_up_em
stock_hsgt_board_rank_em
stock_hsgt_fund_flow_summary_em
stock_hsgt_fund_min_em
stock_hsgt_hist_em
stock_hsgt_hold_stock_em
stock_hsgt_individual_detail_em
stock_hsgt_individual_em
stock_hsgt_institution_statistics_em
stock_hsgt_sh_hk_spot_em
stock_hsgt_stock_statistics_em
stock_index_pb_lg
stock_index_pe_lg
stock_individual_basic_info_hk_xq
stock_individual_basic_info_us_xq
stock_individual_basic_info_xq
stock_individual_fund_flow
stock_individual_fund_flow_rank
stock_individual_info_em
stock_individual_spot_xq
stock_industry_category_cninfo
stock_industry_change_cninfo
stock_industry_clf_hist_sw
stock_industry_pe_ratio_cninfo
stock_info_a_code_name
stock_info_bj_name_code
stock_info_change_name
stock_info_cjzc_em
stock_info_global_cls
stock_info_global_em
stock_info_global_futu
stock_info_global_sina
stock_info_global_ths
stock_info_sh_delist
stock_info_sh_name_code
stock_info_sz_change_name
stock_info_sz_delist
stock_info_sz_name_code
stock_inner_trade_xq
stock_institute_hold
stock_institute_hold_detail
stock_institute_recommend
stock_institute_recommend_detail
stock_intraday_em
stock_intraday_sina
stock_ipo_benefit_ths
stock_ipo_declare_em
stock_ipo_info
stock_ipo_review_em
stock_ipo_summary_cninfo
stock_ipo_tutor_em
stock_irm_ans_cninfo
stock_irm_cninfo
stock_jgdy_detail_em
stock_jgdy_tj_em
stock_js_weibo_nlp_time
stock_js_weibo_report
stock_kc_a_spot_em
stock_lh_yyb_capital
stock_lh_yyb_control
stock_lh_yyb_most
stock_lhb_detail_daily_sina
stock_lhb_detail_em
stock_lhb_ggtj_sina
stock_lhb_hyyyb_em
stock_lhb_jgmmtj_em
stock_lhb_jgmx_sina
stock_lhb_jgstatistic_em
stock_lhb_jgzz_sina
stock_lhb_stock_detail_date_em
stock_lhb_stock_detail_em
stock_lhb_stock_statistic_em
stock_lhb_traderstatistic_em
stock_lhb_yyb_detail_em
stock_lhb_yybph_em
stock_lhb_yytj_sina
stock_lrb_em
stock_main_fund_flow
stock_main_stock_holder
stock_management_change_ths
stock_margin_account_info
stock_margin_detail_sse
stock_margin_detail_szse
stock_margin_ratio_pa
stock_margin_sse
stock_margin_szse
stock_margin_underlying_info_szse
stock_market_activity_legu
stock_market_fund_flow
stock_market_pb_lg
stock_market_pe_lg
stock_new_a_spot_em
stock_new_gh_cninfo
stock_new_ipo_cninfo
stock_news_em
stock_news_main_cx
stock_notice_report
stock_pg_em
stock_price_js
stock_profile_cninfo
stock_profit_forecast_em
stock_profit_forecast_ths
stock_profit_sheet_by_quarterly_em
stock_profit_sheet_by_report_delisted_em
stock_profit_sheet_by_report_em
stock_profit_sheet_by_yearly_em
stock_qbzf_em
stock_qsjy_em
stock_rank_cxd_ths
stock_rank_cxfl_ths
stock_rank_cxg_ths
stock_rank_cxsl_ths
stock_rank_forecast_cninfo
stock_rank_ljqd_ths
stock_rank_ljqs_ths
stock_rank_lxsz_ths
stock_rank_lxxd_ths
stock_rank_xstp_ths
stock_rank_xxtp_ths
stock_rank_xzjp_ths
stock_register_all_em
stock_register_bj
stock_register_cyb
stock_register_db
stock_register_kcb
stock_register_sh
stock_register_sz
stock_report_disclosure
stock_report_fund_hold
stock_report_fund_hold_detail
stock_repurchase_em
stock_research_report_em
stock_restricted_release_detail_em
stock_restricted_release_queue_em
stock_restricted_release_queue_sina
stock_restricted_release_stockholder_em
stock_restricted_release_summary_em
stock_sector_detail
stock_sector_fund_flow_hist
stock_sector_fund_flow_rank
stock_sector_fund_flow_summary
stock_sector_spot
stock_sgt_reference_exchange_rate_sse
stock_sgt_reference_exchange_rate_szse
stock_sgt_settlement_exchange_rate_sse
stock_sgt_settlement_exchange_rate_szse
stock_sh_a_spot_em
stock_share_change_cninfo
stock_share_hold_change_bse
stock_share_hold_change_sse
stock_share_hold_change_szse
stock_shareholder_change_ths
stock_sns_sseinfo
stock_sse_deal_daily
stock_sse_summary
stock_staq_net_stop
stock_sy_em
stock_sy_hy_em
stock_sy_jz_em
stock_sy_profile_em
stock_sy_yq_em
stock_sz_a_spot_em
stock_szse_area_summary
stock_szse_sector_summary
stock_szse_summary
stock_tfp_em
stock_us_daily
stock_us_famous_spot_em
stock_us_hist
stock_us_hist_min_em
stock_us_pink_spot_em
stock_us_spot
stock_us_spot_em
stock_us_valuation_baidu
stock_value_em
stock_xgsglb_em
stock_xgsr_ths
stock_xjll_em
stock_yjbb_em
stock_yjkb_em
stock_yjyg_em
stock_yysj_em
stock_yzxdr_em
stock_zcfz_bj_em
stock_zcfz_em
stock_zdhtmx_em
stock_zh_a_cdr_daily
stock_zh_a_daily
stock_zh_a_disclosure_relation_cninfo
stock_zh_a_disclosure_report_cninfo
stock_zh_a_gbjg_em
stock_zh_a_gdhs
stock_zh_a_gdhs_detail_em
stock_zh_a_hist
stock_zh_a_hist_min_em
stock_zh_a_hist_pre_min_em
stock_zh_a_hist_tx
stock_zh_a_minute
stock_zh_a_new
stock_zh_a_new_em
stock_zh_a_spot
stock_zh_a_spot_em
stock_zh_a_st_em
stock_zh_a_stop_em
stock_zh_a_tick_tx_js
stock_zh_ab_comparison_em
stock_zh_ah_daily
stock_zh_ah_name
stock_zh_ah_spot
stock_zh_ah_spot_em
stock_zh_b_daily
stock_zh_b_minute
stock_zh_b_spot
stock_zh_b_spot_em
stock_zh_dupont_comparison_em
stock_zh_growth_comparison_em
stock_zh_index_daily
stock_zh_index_daily_em
stock_zh_index_daily_tx
stock_zh_index_hist_csindex
stock_zh_index_spot_em
stock_zh_index_spot_sina
stock_zh_index_value_csindex
stock_zh_kcb_daily
stock_zh_kcb_report_em
stock_zh_kcb_spot
stock_zh_scale_comparison_em
stock_zh_valuation_baidu
stock_zh_valuation_comparison_em
stock_zh_vote_baidu
stock_zt_pool_dtgc_em
stock_zt_pool_em
stock_zt_pool_previous_em
stock_zt_pool_strong_em
stock_zt_pool_sub_new_em
stock_zt_pool_zbgc_em
stock_zygc_em
stock_zyjs_ths
sunrise_daily
sunrise_monthly
sw_index_first_info
sw_index_second_info
sw_index_third_cons
sw_index_third_info
tool_trade_date_hist_sina
video_tv
video_variety_show
volatility_yz_rv
xincaifu_rank
```
</details>