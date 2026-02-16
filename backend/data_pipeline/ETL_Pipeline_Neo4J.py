import pandas as pd
from neo4j import GraphDatabase
from pathlib import Path
import re
import time

# -------------------- Neo4j Connection --------------------
URI = "bolt://127.0.0.1:7687"
AUTH = ("neo4j", "12345678")

driver = GraphDatabase.driver(URI, auth=AUTH)

try:
    with driver.session() as session:
        result = session.run("RETURN 1 AS test")
        print("Neo4j connection successful")
except Exception as e:
    print("Neo4j connection failed:", e)
    exit(1)

# -------------------- Paths --------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_FOLDER = BASE_DIR / "data" / "db_30_1_excel"

# -------------------- Clear existing data (optional) --------------------
def clear_database():
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("Database cleared")

# Uncomment if you want to start fresh
# clear_database()

# -------------------- Dataset Configuration --------------------
DATASETS = {
    "Abilities.csv": {
        "node_col": "Element Name",
        "scale_col": "Scale ID",
        "value_col": "Data Value",
        "relationship_prop_map": {"IM": "importance", "LV": "level"},
        "classification": "Ability",
        "node_type": "Ability"
    },
    "Education, Training, and Experience.csv": {
        "node_col": "Element Name",
        "scale_col": "Scale ID",
        "value_col": "Data Value",
        "relationship_prop_map": {"RL": "required_level"},
        "classification": "EducationTrainingExperience",
        "node_type": "Education"
    },
    "Knowledge.csv": {
        "node_col": "Element Name",
        "scale_col": "Scale ID",
        "value_col": "Data Value",
        "relationship_prop_map": {"IM": "importance", "LV": "level"},
        "classification": "Knowledge",
        "node_type": "Knowledge"
    },
    "Skills.csv": {
        "node_col": "Element Name",
        "scale_col": "Scale ID",
        "value_col": "Data Value",
        "relationship_prop_map": {"IM": "importance", "LV": "level"},
        "classification": "Skill",
        "node_type": "Skill"
    },
    "Work Activities.csv": {
        "node_col": "Element Name",
        "scale_col": "Scale ID",
        "value_col": "Data Value",
        "relationship_prop_map": {"IM": "importance", "LV": "level"},
        "classification": "WorkActivity",
        "node_type": "WorkActivity"
    },
    "Technology Skills.csv": {
        "node_col": "Example",
        "extra_props": ["Commodity Title", "Hot Technology", "In Demand"],
        "classification": "TechnologySkill",
        "node_type": "TechnologySkill",
        "is_tech": True
    },
    "Tools Used.csv": {
        "node_col": "Example",
        "extra_props": ["Commodity Title"],
        "classification": "Tool",
        "node_type": "Tool",
        "is_tool": True
    }
}

# -------------------- Neo4j Write Functions --------------------
def create_or_update_job(tx, job_soc, job_title):
    """Create or update a job node"""
    job_key = f"{job_soc} | {job_title}"
    
    tx.run("""
        MERGE (j:Job {jobKey: $job_key})
        SET j.SOC = $job_soc,
            j.title = $job_title
        RETURN j
    """, job_key=job_key, job_soc=job_soc, job_title=job_title)

def create_or_update_skill(tx, node_name, classification, node_type):
    """Create or update a skill node with classification"""
    tx.run("""
        MERGE (s:Skill {name: $node_name})
        SET s.classification = 
            CASE
                WHEN s.classification IS NULL THEN [$classification]
                WHEN NOT $classification IN s.classification THEN s.classification + $classification
                ELSE s.classification
            END,
            s.type = $node_type
        RETURN s
    """, node_name=node_name, classification=classification, node_type=node_type)

def create_relationship(tx, job_key, node_name, rel_props):
    """Create or update relationship between job and skill"""
    tx.run("""
        MATCH (j:Job {jobKey: $job_key})
        MATCH (s:Skill {name: $node_name})
        MERGE (j)-[r:REQUIRES]->(s)
        SET r += $rel_props
    """, job_key=job_key, node_name=node_name, rel_props=rel_props)

# -------------------- Import Function --------------------
def import_dataset(file_name, config):
    print(f"\nImporting {file_name}...")
    file_path = DATA_FOLDER / file_name
    
    if not file_path.exists():
        print(f"  File not found: {file_name}, skipping...")
        return
    
    # Read CSV
    df = pd.read_csv(file_path)
    print(f"  Total rows: {len(df)}")
    
    # Sample check for abilities
    if file_name == "Abilities.csv":
        oral_rows = df[df["Element Name"] == "Oral Expression"]
        print(f"  Found {len(oral_rows)} rows for 'Oral Expression'")
        if len(oral_rows) > 0:
            print(f"  Sample: {oral_rows[['Title', 'Scale ID', 'Data Value']].head(2).to_dict('records')}")
    
    with driver.session() as session:
        processed = 0
        errors = 0
        
        for idx, row in df.iterrows():
            try:
                # Extract basic data
                soc = str(row["O*NET-SOC Code"])
                title = str(row["Title"])
                node_name = str(row[config["node_col"]])
                
                # Create job key
                job_key = f"{soc} | {title}"
                
                # Create/update job node
                session.execute_write(create_or_update_job, soc, title)
                
                # Create/update skill node with classification
                session.execute_write(
                    create_or_update_skill, 
                    node_name, 
                    config["classification"],
                    config.get("node_type", "Skill")
                )
                
                # Prepare relationship properties
                rel_props = {}
                
                # Handle scale-based properties (Abilities, Knowledge, Skills, etc.)
                if "scale_col" in config and "value_col" in config:
                    scale = row[config["scale_col"]]
                    value = row[config["value_col"]]
                    
                    # Convert to float if possible
                    try:
                        value = float(value)
                    except:
                        pass
                    
                    prop_name = config["relationship_prop_map"].get(scale)
                    if prop_name:
                        rel_props[prop_name] = value
                
                # Handle extra properties (Technology Skills, Tools)
                if "extra_props" in config:
                    for col in config["extra_props"]:
                        if col in row and pd.notna(row[col]):
                            prop_key = re.sub(r"\s+", "_", col)
                            rel_props[prop_key] = row[col]
                
                # Create relationship
                if rel_props:
                    session.execute_write(create_relationship, job_key, node_name, rel_props)
                
                processed += 1
                
                # Progress indicator
                if processed % 1000 == 0:
                    print(f"  Processed {processed} rows...")
                    
            except Exception as e:
                errors += 1
                if errors < 5:  # Only print first few errors
                    print(f"  Error on row {idx}: {e}")
        
        print(f"  Completed {file_name}: {processed} rows processed, {errors} errors")

# -------------------- Main Import --------------------
def main():
    start_time = time.time()
    
    for file_name, config in DATASETS.items():
        import_dataset(file_name, config)
    
    # Create indexes for better performance
    print("\nCreating indexes...")
    with driver.session() as session:
        session.run("CREATE INDEX IF NOT EXISTS FOR (j:Job) ON (j.jobKey)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (j:Job) ON (j.SOC)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (s:Skill) ON (s.name)")
        print("Indexes created")
    
    elapsed_time = time.time() - start_time
    print(f"\nImport completed in {elapsed_time:.2f} seconds!")
    
    # Verification
    print("\nVerifying import...")
    with driver.session() as session:
        # Check total nodes
        result = session.run("MATCH (n) RETURN count(n) as count")
        total_nodes = result.single()["count"]
        print(f"  Total nodes: {total_nodes}")
        
        # Check classifications
        result = session.run("""
            MATCH (s:Skill)
            RETURN s.classification, count(*) as count
            ORDER BY count DESC
            LIMIT 10
        """)
        print("  Classifications:")
        for record in result:
            print(f"    - {record['s.classification']}: {record['count']}")
        
        # Specifically check for Oral Expression
        result = session.run("""
            MATCH (s:Skill {name: 'Oral Expression'})
            RETURN s.name, s.classification
        """)
        if result.peek():
            record = result.single()
            print(f"  Found: {record['s.name']} with classification {record['s.classification']}")
        else:
            print("  Oral Expression NOT found - check import")

if __name__ == "__main__":
    main()
    driver.close()