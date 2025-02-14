const fs = require('fs').promises;

const DELIMITER = '|||'; // Define a constant for the delimiter

/**
 * Convert hallmarks array into a readable string
 * @param {Array} hallmarks 
 * @returns {string}
 */
function flattenHallmarks(hallmarks) {
    if (!hallmarks || !hallmarks.length) {
        return "";
    }
    return hallmarks
        .map(([timestamp, event]) => {
            const date = new Date(timestamp * 1000).toISOString().split('T')[0];
            return `${date}: ${event}`;
        })
        .join("; ");
}

/**
 * Separate regular TVL and borrowed TVL into clean key names
 * @param {Object} chainTvls 
 * @returns {Object}
 */
function processChainTvls(chainTvls) {
    const regularTvls = {};
    const borrowedTvls = {};

    Object.entries(chainTvls).forEach(([chain, value]) => {
        if (chain.endsWith('-borrowed')) {
            const chainName = chain.replace('-borrowed', '');
            borrowedTvls[`${chainName}_borrowed`] = value;
        } else {
            regularTvls[`${chain}_tvl`] = value;
        }
    });

    return { ...regularTvls, ...borrowedTvls };
}

/**
 * Transform a single protocol into a flattened format
 * @param {Object} protocol 
 * @returns {Object}
 */
function transformProtocol(protocol) {
    const indexProtocolData = protocol.index_metrics || {};
    const tvlBreakdown = protocol.tvl_breakdown || {};
    
    return {
        id: protocol.id,
        name: protocol.name,
        content: `
[PROTOCOL OVERVIEW]
${protocol.name} (${protocol.symbol}) is a ${protocol.category} protocol ${protocol.description || ''}. 
Located at address ${protocol.address}, it operates on the following chains: ${(protocol.chains || []).join(', ')}.
Website: ${protocol.url || 'Not provided'}

[TECHNICAL DETAILS]
- Oracle Integration: ${(protocol.oracles || []).join(', ')}
- Forked From: ${(protocol.forkedFrom || []).length ? protocol.forkedFrom.join(', ') : 'Original Protocol'}
- Audit Status: ${protocol.audits || 0} audits completed ${protocol.audit_links ? `(${protocol.audit_links.join(', ')})` : ''}
- Listed Since: ${protocol.listed_at || 'Unknown'}

[KEY METRICS]
- Total Value Locked (TVL): $${protocol.tvl || 0}
- Market Cap: $${protocol.mcap || 0}
- TVL Changes:
  * 24h: ${protocol.change_1h || 0}%
  * 7d: ${protocol.change_7d || 0}%
  * 30d: ${protocol.change_30d || 0}%

[FINANCIAL PERFORMANCE]
- Fees (24h): $${indexProtocolData.fees_24h || 0}
- Revenue (24h): $${indexProtocolData.revenue_24h || 0}
- Volume (24h): $${indexProtocolData.volume_24h || 0}
- Treasury Revenue: $${indexProtocolData.treasury_revenue_24h || 0}

[CHAIN-SPECIFIC TVL]
${Object.entries(protocol.chainTvls || {})
    .map(([chain, value]) => `- ${chain}: $${value}`)
    .join('\n')}

[ADDITIONAL INFORMATION]
- Website: ${protocol.url || 'Not provided'}
- Social: ${protocol.twitter ? `Twitter: @${protocol.twitter}` : 'No social media information'}
- Parent Protocol: ${protocol.parent_protocol || 'Independent protocol'}
- Methodology: ${protocol.methodology || 'No methodology provided'}

[HISTORICAL EVENTS]
${protocol.hallmarks ? protocol.hallmarks : 'No significant historical events recorded'}

[RAW METRICS]
${JSON.stringify({
    token_breakdowns: protocol.token_breakdowns,
    extra_tvl: protocol.extra_tvl,
    index_metrics: protocol.index_metrics,
    tvl_breakdown: protocol.tvl_breakdown
}, null, 2)}`,
        metadata: {
            category: protocol.category,
            chains: protocol.chains,
            tvl: protocol.tvl,
            audit_count: protocol.audits,
            url: protocol.url,
            last_updated: new Date().toISOString()
        }
    };
}

/**
 * Transform index data into a flattened format
 * @param {Object} indexData 
 * @returns {Object}
 */
function transformIndexData(indexData) {
    return {
        chains: indexData.pageProps.chainsSet || [],
        protocols_list: indexData.pageProps.protocolsList || [],
        total_funding_amount: indexData.pageProps.totalFundingAmount,
        chain_token_info: indexData.pageProps.chainTokenInfo,
        chain_treasury: indexData.pageProps.chainTreasury,
        chain_raises: indexData.pageProps.chainRaises,
        chain_assets: indexData.pageProps.chainAssets
    };
}

/**
 * Merge protocol and chain data
 * @param {Array} protocols 
 * @param {Object} indexData 
 * @returns {Array}
 */
function mergeData(protocols, indexData) {
    // Create a map of protocol names for quick lookup
    const protocolMap = new Map(
        indexData.protocols_list?.map(p => [p.name, p]) || []
    );
    
    return protocols.map(protocol => {
        const indexProtocolData = protocolMap.get(protocol.name) || {};
        
        return {
            ...protocol,
            // Add detailed metrics from index data
            index_metrics: {
                // Volume metrics
                volume_24h: indexProtocolData.volume_24h,
                volume_7d: indexProtocolData.volume_7d,
                cumulative_volume: indexProtocolData.cumulativeVolume,
                
                // Fee metrics
                fees_24h: indexProtocolData.fees_24h,
                fees_7d: indexProtocolData.fees_7d,
                fees_30d: indexProtocolData.fees_30d,
                cumulative_fees: indexProtocolData.cumulativeFees,
                
                // Revenue metrics
                revenue_24h: indexProtocolData.revenue_24h,
                revenue_7d: indexProtocolData.revenue_7d,
                revenue_30d: indexProtocolData.revenue_30d,
                
                // Holder metrics
                holder_revenue_24h: indexProtocolData.holderRevenue_24h,
                holders_revenue_30d: indexProtocolData.holdersRevenue30d,
                
                // Supply side metrics
                supply_side_revenue_24h: indexProtocolData.supplySideRevenue_24h,
                
                // Treasury metrics
                treasury_revenue_24h: indexProtocolData.treasuryRevenue_24h,
                
                // User metrics
                user_fees_24h: indexProtocolData.userFees_24h,
                
                // Performance metrics
                pf: indexProtocolData.pf,
                ps: indexProtocolData.ps
            },
            
            // Add TVL breakdowns
            tvl_breakdown: {
                tvl_prev_day: indexProtocolData.tvlPrevDay,
                tvl_prev_week: indexProtocolData.tvlPrevWeek,
                tvl_prev_month: indexProtocolData.tvlPrevMonth
            }
        };
    });
}

/**
 * Convert array to CSV string
 * @param {Array} data 
 * @returns {string}
 */
function arrayToCSV(data) {
    if (!data.length) return '';
    
    const sections = ['basic_info', 'technical_info', 'metrics', 'social_audit', 'revenue_fees', 'raw_data'];
    const headers = sections;
    const csvRows = [];
    
    // Add header row
    csvRows.push(headers.join('\t')); // Using tab as delimiter between sections
    
    // Add data rows
    data.forEach(row => {
        const values = headers.map(header => {
            const val = row[header];
            // Escape any existing delimiters in the content
            return `"${String(val).replace(/"/g, '""')}"`;
        });
        csvRows.push(values.join('\t'));
    });
    
    return csvRows.join('\n');
}

async function main() {
    try {
        const [protocolsData, indexData] = await Promise.all([
            fs.readFile('protocols.json', 'utf8'),
            fs.readFile('index.json', 'utf8')
        ]);

        const protocols = JSON.parse(protocolsData);
        const index = JSON.parse(indexData);
        const transformedProtocols = protocols.map(transformProtocol);
        
        // Create text content for each protocol
        const textContent = transformedProtocols
            .map((protocol, index, array) => {
                const doc = `[DOCUMENT START]
ID: ${protocol.id}
NAME: ${protocol.name}

${protocol.content}
[DOCUMENT END]`;
                
                // Add separator only if it's not the last document
                return index === array.length - 1 ? doc : `${doc}\n\n---\n\n`;
            })
            .join('');

        // Save as text file
        await fs.writeFile('protocols_for_rag.txt', textContent);

        console.log('Transformation complete! File saved:');
        console.log('- protocols_for_rag.txt');
    } catch (error) {
        console.error('Error:', error);
        process.exit(1);
    }
}

main(); 