import json
from typing import Dict, Any
import pandas as pd
from datetime import datetime

def flatten_hallmarks(hallmarks: list) -> str:
    """Convert hallmarks array into a readable string."""
    if not hallmarks:
        return ""
    return "; ".join([f"{datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')}: {event}" 
                     for timestamp, event in hallmarks])

def process_chain_tvls(chain_tvls: Dict[str, float]) -> Dict[str, float]:
    """Separate regular TVL and borrowed TVL into clean key names."""
    regular_tvls = {}
    borrowed_tvls = {}
    
    for chain, value in chain_tvls.items():
        if chain.endswith('-borrowed'):
            chain_name = chain.replace('-borrowed', '')
            borrowed_tvls[f"{chain_name}_borrowed"] = value
        else:
            regular_tvls[f"{chain_name}_tvl"] = value
    
    return {**regular_tvls, **borrowed_tvls}

def transform_protocol(protocol: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a single protocol into a flattened format."""
    transformed = {
        'id': protocol.get('id'),
        'name': protocol.get('name'),
        'address': protocol.get('address'),
        'symbol': protocol.get('symbol'),
        'url': protocol.get('url'),
        'description': protocol.get('description'),
        'category': protocol.get('category'),
        'chains': ', '.join(protocol.get('chains', [])),
        'oracles': ', '.join(protocol.get('oracles', [])),
        'forked_from': ', '.join(protocol.get('forkedFrom', [])),
        'twitter': protocol.get('twitter'),
        'audit_count': protocol.get('audits'),
        'audit_links': ', '.join(protocol.get('audit_links', [])),
        'listed_at': datetime.fromtimestamp(protocol.get('listedAt', 0)).strftime('%Y-%m-%d'),
        'parent_protocol': protocol.get('parentProtocol'),
        'methodology': protocol.get('methodology'),
        'total_tvl': protocol.get('tvl'),
        'hallmarks': flatten_hallmarks(protocol.get('hallmarks', [])),
        'change_1h': protocol.get('change_1h'),
        'change_1d': protocol.get('change_1d'),
        'change_7d': protocol.get('change_7d'),
    }
    
    # Add chain-specific TVLs
    chain_tvls = process_chain_tvls(protocol.get('chainTvls', {}))
    transformed.update(chain_tvls)
    
    return transformed

def main():
    # Read the protocols file
    with open('protocols.json', 'r') as f:
        protocols = json.load(f)
    
    # Transform all protocols
    transformed_protocols = [transform_protocol(protocol) for protocol in protocols]
    
    # Convert to DataFrame for easier handling
    df = pd.DataFrame(transformed_protocols)
    
    # Save as CSV (easy to import into vector databases)
    df.to_csv('transformed_protocols.csv', index=False)
    
    # Save as JSON (alternative format)
    with open('transformed_protocols.json', 'w') as f:
        json.dump(transformed_protocols, f, indent=2)

if __name__ == "__main__":
    main() 