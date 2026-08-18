# -*- coding: utf-8 -*-
"""
Created on Sat Aug 31 23:29:23 2024

@author: shank
"""
#!/usr/bin/env python3

"""
GraphAnalysis_Final.py

This script constructs and analyzes a directed graph representing Sanskrit Antyākṣarī gameplay.
It processes a dataset of Sanskrit verses, builds a directed graph based on the first and last 
letters of each verse, and applies advanced graph algorithms for various analyses, including.:

1. **Graph Construction**:
   - Nodes represent verses with attributes: first letter, last letter, swara after last, chapter, verse number, and cumulative number.
   - Edges connect verses based on matching conditions.

2. **Graph Analysis**:
   - Identification of **source nodes** (no incoming edges), **sink nodes** (no outgoing edges), and **isolated nodes**.
   - Computation of the **longest path** in a cyclic graph using DFS-based backtracking.
   - Identification of the **biggest cycle** in the graph.

3. **Graph Visualization**:
   - Renders the directed graph with distinct colors for source, sink, and isolated nodes.
   - Highlights the **longest path** in orange and the **biggest cycle** in blue.
   - Labels nodes with Devanagari script for proper Sanskrit representation.

This program is part of a study on **Optimizing Sanskrit Antyakshari using Directed Graphs**.
It provides insights into verse connectivity, verse transition rules, and competitive strategies 
for playing Antyākṣarī.

Author: **Shankararama Sharma**  
Affiliation: **Vyoma Linguistic Labs Foundation**  
Date: **February 11, 2025**
"""

import pandas as pd
import csv
import networkx as nx
import matplotlib.pyplot as plt
import re
import time
from collections import Counter

# Load the CSV Data
def load_csv_data(csv_file):
    nodes = []
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            #Verse,First Letter,Last Letter,Swara After Last,Chapter,Verse Number,Cumulative Number
            verse = row["Verse"]
            first_letter = row['First Letter']
            last_letter = row['Last Letter']
            swara_after_last = row['Swara After Last']
            chapter = row["Chapter"]
            verse_number = row["Verse Number"]
            cum_num = row["Cumulative Number"]
            nodes.append((first_letter, last_letter, swara_after_last, 
                          chapter, verse_number, cum_num, verse))
    return nodes

# Function to extract the first consonant sequence followed by the first vowel
def extract_initial_consonants_and_vowel(s):
    # match = re.match(r'^([^aAiIuUeEoO]*)(?=[aAiIuUeEoO]|$)', s)
    match = re.match(r'^([^aAiIuUeEoOR\^]*)(?=[aAiIuUeEoOR\^]|$)', s) # with R-kara
    return match.group(0) if match else ''

# Create the Directed Graph with the new matching condition
def create_directed_graph(nodes):
    G = nx.DiGraph()
    
    # Add nodes to the graph
    for idx, node in enumerate(nodes):
        G.add_node(idx, first_letter=node[0], last_letter=node[1], swara_after_last=node[2],
                   chapter=node[3], verse_number=node[4], cum_num=node[5], verse=node[6])
    
    # Add edges based on the new matching condition
    for i, (first_letter_1, last_letter_1, swara_after_last_1, 
            chapter, verse_number, cum_num, verse) in enumerate(nodes):
        for j, (first_letter_2, last_letter_2, _,
                chapter, verse_number, cum_num, verse) in enumerate(nodes):
            if i != j:
                # Extract the sequence of consonants and first vowel from the first letter
                initial_sequence = extract_initial_consonants_and_vowel(first_letter_2)
                if last_letter_1 == initial_sequence:
                    G.add_edge(i, j)
    
    return G

# Create the Directed Graph with the new matching condition
def create_directed_graph_swara(nodes):
    G = nx.DiGraph()

    # Add nodes to the graph
    for idx, node in enumerate(nodes):
        G.add_node(idx, first_letter=node[0], last_letter=node[1], swara_after_last=node[2],
                   chapter=node[3], verse_number=node[4], cum_num=node[5], verse=node[6])
    
    # Add edges based on the new matching condition
    for i, (first_letter_1, last_letter_1, swara_after_last_1, 
            chapter, verse_number, cum_num, verse) in enumerate(nodes):
        connected = False
        for j, (first_letter_2, last_letter_2, _,
                chapter, verse_number, cum_num, verse) in enumerate(nodes):
            if i != j:
                initial_sequence = extract_initial_consonants_and_vowel(first_letter_2)
                if last_letter_1 == initial_sequence:
                    G.add_edge(i, j)
                    connected = True
        
        # If no direct connection is found, use 'Swara After Last'
        if not connected:
            for j, (first_letter_2, last_letter_2, _,
                    chapter, verse_number, cum_num, verse) in enumerate(nodes):
                if i != j and swara_after_last_1 == extract_initial_consonants_and_vowel(first_letter_2):
                    G.add_edge(i, j)
    
    return G

# Find the Longest Path in a Directed Graph (Handling Cycles without Removing Them)
def find_longest_path_with_cycle_handling(G):
    memo = {}  # Memoization dictionary to store the longest path from each node
    visited = set()
    stack = set()  # Stack to track recursion depth for cycle detection
    
    def dfs(node):
        if node in memo:
            return memo[node]
        if node in stack:
            return []  # If a cycle is detected, return an empty path
        
        stack.add(node)
        max_path = []
        for neighbor in G.successors(node):
            path = dfs(neighbor)
            if len(path) > len(max_path):
                max_path = path
        
        stack.remove(node)
        memo[node] = [node] + max_path
        return memo[node]
    
    longest_path = []
    for node in G.nodes():
        if node not in visited:
            path = dfs(node)
            if len(path) > len(longest_path):
                longest_path = path
    
    return longest_path

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

# Function to find the shortest path from a given letter to a sink node
def find_shortest_path_to_sink(G, letter):
    start_nodes = [node for node in G.nodes() if G.nodes[node]['first_letter'] == letter]
    sink_nodes = [node for node in G.nodes() if G.out_degree(node) == 0 and G.in_degree(node) > 0]
    
    shortest_path = None
    for start in start_nodes:
        for sink in sink_nodes:
            try:
                path = nx.shortest_path(G, source=start, target=sink)
                if shortest_path is None or len(path) < len(shortest_path):
                    shortest_path = path
            except nx.NetworkXNoPath:
                continue
    
    return shortest_path
        
# Function to find unique first letters of source nodes
def find_unique_first_letters_of_source_nodes(G):
    return set(G.nodes[node]['first_letter'] for node in G.nodes() if G.in_degree(node) == 0 and G.out_degree(node) > 0)

# Function to find isolated nodes (nodes with no incoming or outgoing edges)
def find_isolated_nodes(G):
    return [(node, G.nodes[node]['first_letter'], G.nodes[node]['last_letter']) for node in G.nodes() if G.in_degree(node) == 0 and G.out_degree(node) == 0]

# Function to find unique first and last letters of isolated nodes
def find_unique_letters_of_isolated_nodes(G):
    return set((G.nodes[node]['first_letter'], G.nodes[node]['last_letter']) for node in G.nodes() if G.in_degree(node) == 0 and G.out_degree(node) == 0)


csv_file = 'BG_info.csv'
# csv_file = 'Narayaneeyam_info.csv'
# csv_file = 'BG_Nar_Info.csv'
nodes = load_csv_data(csv_file)
# Ensure G is a NetworkX graph before calling the function
# G = create_directed_graph_swara(nodes)  # Ensure `nodes` is a NetworkX DiGraph
G = create_directed_graph(nodes)
# shortest_path = find_shortest_path_to_sink(nodes, 'ए')

# List of Devanagari letters to check
devanagari_letters = ['अ', 'आ', 'इ', 'ई', 'उ', 'ऊ', 'ए', 'ऐ', 'ओ', 'औ', 
                      'क', 'ख', 'ग', 'घ', 'ङ', 'च', 'छ', 'ज', 'झ', 'ञ', 
                      'ट', 'ठ', 'ड', 'ढ', 'ण', 'त', 'थ', 'द', 'ध', 'न', 
                      'प', 'फ', 'ब', 'भ', 'म', 'य', 'र', 'ल', 'व', 
                      'श', 'ष', 'स', 'ह']

# Iterate over each letter and find the shortest path
for letter in devanagari_letters:
    shortest_path = find_shortest_path_to_sink(G, letter)
    print(f"Shortest path for letter '{letter}': {shortest_path if shortest_path else 'No path found'}")

## Handle Cyclic Graph also
start_time = time.time()
longest_path = find_longest_path_with_cycle_handling(G)
print("Longest Acyclic Path (in terms of nodes):", longest_path)
print("Time taken: ", time.time() - start_time)
print("Length of Longest path = ", len(longest_path))

## Handle Cyclic Graph - method 2
start_time = time.time()
longest_path = find_longest_path_in_cyclic_graph(G)
print("Longest Acyclic Path (in terms of nodes):", longest_path)
print("Time taken: ", time.time() - start_time)
print("Length of Longest path = ", len(longest_path))

df = pd.read_csv(csv_file)

# Count the frequency of first and last letters
first_letter_counts = Counter(df["First Letter"])
last_letter_counts = Counter(df["Last Letter"])

# Find the most frequent first and last letters
most_frequent_first_letter = first_letter_counts.most_common(1)[0]
most_frequent_last_letter = last_letter_counts.most_common(1)[0]

# Find nodes with highest in-degree and out-degree
highest_in_degree_node = max(G.nodes, key=lambda node: G.in_degree(node))
highest_out_degree_node = max(G.nodes, key=lambda node: G.out_degree(node))

# Find the node with the highest sum of in-degree + out-degree
highest_total_degree_node = max(G.nodes, key=lambda node: G.in_degree(node) + G.out_degree(node))

# Print results
print("Most Frequent First Letter:", most_frequent_first_letter)
print("Most Frequent Last Letter:", most_frequent_last_letter)
print(f"Highest In-Degree Node: {highest_in_degree_node}, Degree: {G.in_degree(highest_in_degree_node)}")
print(f"Highest Out-Degree Node: {highest_out_degree_node}, Degree: {G.out_degree(highest_out_degree_node)}")
print(f"Highest Total Degree Node: {highest_total_degree_node}, Degree: {G.in_degree(highest_total_degree_node) + G.out_degree(highest_total_degree_node)}")

