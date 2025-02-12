# **Optimizing Sanskrit Antyakshari with Directed Graphs**  
_A Competitive and Strategic Tool for Enhanced Play_

## **Overview**
This repository contains the implementation of a **graph-based analysis of Sanskrit Antyākṣarī**, a game where each verse must start with the last letter of the previous verse. The project models this **verse transition as a directed graph (DiGraph)** and applies advanced **graph algorithms** to analyze connectivity, cycles, and paths.

This work is part of a research study on **Computational Sanskrit and Digital Humanities**, optimizing the playability and strategic depth of Antyākṣarī using **Graph Theory and NetworkX**.

## **Features**
- **Graph Construction**  
  - Nodes represent Sanskrit verses with **first letter, last letter, swara after last, chapter, verse number, and cumulative number**.  
  - Edges are added when one verse can follow another.  

- **Graph Analysis**  
  - Identifies **source nodes (blue), sink nodes (red), and isolated nodes (green)**.  
  - Computes the **longest path in a cyclic graph** using DFS-based exploration.  
  - Detects **cycles and the largest cycle** to prevent infinite loops in gameplay.  
  - Finds **shortest paths to sink nodes** to analyze dead ends in the game.  
  - Analyzes **degree distribution** to determine frequent transitions.  

- **Graph Visualization**  
  - Uses **NetworkX and Matplotlib** for clear representation.  
  - Highlights **biggest cycle in blue** and **longest path in orange**.  
  - Renders **Devanagari script labels** using `NotoSansDevanagari-Bold.ttf`.  
  - Saves **high-resolution PDF outputs** for research and presentations.  

---

## **Repository Structure**
```plaintext
📂 Sanskrit_Antyakshari_Graph
│── 📄 README.md                # Project documentation
│── 📄 Antyakshari_Graph.py    # Core graph construction and analysis script
│── 📄 Antyakshari_visualisation.py # High-resolution graph visualization script
│── 📄 BG_info.csv               # Bhagavad Gita verses with graph attributes
│── 📄 Narayaneeyam_info.csv     # Narayaneeyam verses with graph attributes
