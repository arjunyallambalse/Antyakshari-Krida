# -*- coding: utf-8 -*-
"""
Created on Tue Feb 11 14:40:41 2025

@author: shank
"""

"""
FinalAnalysis_ForPaper.py

This script performs advanced graph-based analysis on Sanskrit verses for the **Antyākṣarī game** 
using **Directed Graphs (DiGraphs)**. It is specifically designed for generating high-quality 
visualizations and analysis for research publication.

1. **Graph Construction**:
   - Nodes represent verses with attributes: first letter, last letter, swara after last, chapter, and verse number.
   - Edges connect verses based on their last and first letters.

2. **Graph Analysis**:
   - Computes the **longest path** in a cyclic graph using DFS-based exploration.
   - Identifies **source nodes, sink nodes, and isolated nodes**.
   - Highlights **cycles and the largest cycle** in the graph.

3. **Graph Visualization**:
   - Renders the graph using **circular layout** for better clarity.
   - Distinguishes **source (blue), sink (red), and isolated (green) nodes**.
   - Highlights the **biggest cycle in blue** and the **longest path in orange**.
   - Uses **Devanagari script labels** for proper representation of Sanskrit text.
   - Outputs a **high-resolution PDF** with a transparent background for publication.

This script is a part of the research on **"Optimizing Sanskrit Antyakshari with Directed Graphs"**, 
submitted to the **Computational Sanskrit and Digital Humanities** section of **WSC18**.

Author: **Shankararama Sharma**  
Affiliation: **Vyoma Linguistic Labs Foundation**  
Date: **February 11, 2025**
"""

import networkx as nx
import matplotlib.pyplot as plt
import csv
import matplotlib.font_manager as fm

# Manually set the font path (update this based on the output from the script above)
font_path = "C:\\Users\\shank\\AppData\\Local\\Microsoft\\Windows\\Fonts\\NotoSansDevanagari-Bold.ttf"
devanagari_font = fm.FontProperties(fname=font_path, size=12)

def find_longest_path_in_cyclic_graph(G):
    longest_path = []
    
    def dfs(node, path, visited):
        """ Recursive DFS to find the longest simple path, handling cycles. """
        nonlocal longest_path
        
        if node in visited:  # If cycle detected, stop exploration for this path
            return

        path.append(node)
        visited.add(node)

        # If the current path is longer, update the longest path found
        if len(path) > len(longest_path):
            longest_path = path.copy()
        
        # Explore all neighbors
        for neighbor in G.successors(node):
            dfs(neighbor, path, visited)

        # Backtrack to explore other paths
        path.pop()
        visited.remove(node)

    # Try DFS from all nodes to ensure we find the longest path
    for node in G.nodes():
        dfs(node, [], set())

    return longest_path

# Function to visualize the full graph with proper Devanagari rendering
def visualize_full_graph(G, output_file="graph_visualization.pdf"):
    plt.figure(figsize=(8, 6), dpi=300, facecolor='none')  # High-resolution figure with transparent background
    
    # Use a compact graph layout
    pos = nx.circular_layout(G)
    
    # Identify different types of nodes
    source_nodes = [node for node in G.nodes() if G.in_degree(node) == 0 and G.out_degree(node) > 0]
    sink_nodes = [node for node in G.nodes() if G.out_degree(node) == 0 and G.in_degree(node) > 0]
    isolated_nodes = list(nx.isolates(G))
    
    # Find all cycles and identify the largest one
    cycles = list(nx.simple_cycles(G))
    biggest_cycle = max(cycles, key=len) if cycles else []
    cycle_edges = [(biggest_cycle[i], biggest_cycle[i + 1]) for i in range(len(biggest_cycle) - 1)]
    if biggest_cycle:
        cycle_edges.append((biggest_cycle[-1], biggest_cycle[0]))  # Complete the cycle    
    
    # Draw the graph (without labels to avoid issues)
    nx.draw(G, pos, with_labels=False, node_size=3000, node_color='lightgray', 
            font_size=16, font_weight='bold', edge_color='gray', alpha=0.9)
    
    # Draw special node categories
    nx.draw_networkx_nodes(G, pos, nodelist=source_nodes, node_color='blue', node_size=3000)
    nx.draw_networkx_nodes(G, pos, nodelist=sink_nodes, node_color='red', node_size=3000)
    nx.draw_networkx_nodes(G, pos, nodelist=isolated_nodes, node_color='green', node_size=3000)
    
    # Draw all edges with larger arrowheads
    nx.draw_networkx_edges(G, pos, edgelist=G.edges(), edge_color='gray', width=3, arrows=True, arrowstyle='-|>', arrowsize=20, node_size=3000)
    
    # Highlight biggest cycle edges in blue
    nx.draw_networkx_edges(G, pos, edgelist=cycle_edges, edge_color='blue', width=3, arrows=True, arrowstyle='-|>', arrowsize=20, node_size=3000)
    
    # Find the longest path
    longest_path = find_longest_path_in_cyclic_graph(G)
    longest_path_edges = [(longest_path[i], longest_path[i + 1]) for i in range(len(longest_path) - 1)]
    
    # Highlight longest path edges in orange, avoiding cycle overlap
    # offset_pos = {node: (x + 0.03, y + 0.03) if node in biggest_cycle else (x, y) for node, (x, y) in pos.items()}
    nx.draw_networkx_edges(G, pos, edgelist=longest_path_edges, edge_color='orange', width=3, arrows=True, arrowstyle='-|>', arrowsize=20, alpha=0.8, node_size=3000)
    
    # Add node labels with chapter and verse number
    for node in G.nodes():
        x, y = pos[node]
        label_text = f"{G.nodes[node]['first_letter']},{G.nodes[node]['last_letter']},{G.nodes[node]['swara_after_last']}\n({G.nodes[node]['chapter']}.{G.nodes[node]['verse_number']})"
        plt.text(x, y, label_text, fontproperties=devanagari_font, fontsize=14, ha='center', va='center', bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))
        
    # Add edge labels for longest path numbering
    edge_labels = {longest_path_edges[i]: str(i + 1) for i in range(len(longest_path_edges))}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, label_pos=0.45,
                                  font_color='black', font_size=12, font_weight='bold')
    
    # Save as a high-resolution PDF with transparent background
    plt.savefig(output_file, format="pdf", bbox_inches="tight", transparent=True)
    plt.show()
    
    print(f"Graph saved as {output_file}")

# Load the CSV Data
def load_csv_data(csv_file):
    nodes = []
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            first_letter = row['First Letter']
            last_letter = row['Last Letter']
            swara_after_last = row['Swara After Last']
            chapter = row["Chapter"]
            verse_number = row["Verse Number"]
            cum_num = row["Cumulative Number"]
            nodes.append((first_letter, last_letter, swara_after_last, chapter, verse_number, cum_num))
    return nodes

# Create the Directed Graph
def create_directed_graph(nodes):
    G = nx.DiGraph()
    
    # Add nodes to the graph
    for idx, node in enumerate(nodes):
        G.add_node(idx, first_letter=node[0], last_letter=node[1], swara_after_last=node[2],
                   chapter=node[3], verse_number=node[4], cumulative_number=node[5])
    
    # Add edges based on matching last letter to first letter
    for i, (first_letter_1, last_letter_1, swara_after_last_1, _, _, _) in enumerate(nodes):
        connected = False
        for j, (first_letter_2, last_letter_2, swara_after_last_2, _, _, _) in enumerate(nodes):
            if i != j and last_letter_1 == first_letter_2:
                G.add_edge(i, j)
                connected = True
        
        # If no direct connection is found, use 'Swara After Last'
        if not connected:
            for j, (first_letter_2, last_letter_2, swara_after_last_2, _, _, _) in enumerate(nodes):
                if i != j and swara_after_last_1 == first_letter_2:
                    G.add_edge(i, j)
    
    return G

# Main Execution
csv_file = "sample_Info_nar.csv"  # Change this to your actual CSV file
nodes = load_csv_data(csv_file)
G = create_directed_graph(nodes)
visualize_full_graph(G)

