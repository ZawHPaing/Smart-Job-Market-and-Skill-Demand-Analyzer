import pandas as pd
from neo4j import GraphDatabase
from pathlib import Path
import re

# -------------------- Neo4j Connection --------------------
URI = "bolt://127.0.0.1:7687"
AUTH = ("neo4j", "12345678")  # change if needed

driver = GraphDatabase.driver(URI, auth=AUTH)

try:
    with driver.session() as session:
        result = session.run("RETURN 1 AS test")
        print("Neo4j connection successful. Result:", result.single()["test"])
except Exception as e:
    print("Neo4j connection failed:", e)
    exit(1)

# -------------------- Paths --------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_FOLDER = BASE_DIR / "data" / "db_30_1_excel"

# -------------------- Dataset Configuration --------------------
DATASETS = {
    "Abilities.csv": {
        "node_col": "Element Name",
        "scale_col": "Scale Name",
        "value_col": "Data Value",
        "relationship_prop_map": {"IM": "importance", "LV": "level"},
        "classification": "Ability"
    },
    "Education, Training, and Experience.csv": {
        "node_col": "Element Name",
        "scale_col": "Scale Name",
        "value_col": "Data Value",
        "relationship_prop_map": {"RL": "required_level"},
        "classification": "EducationTrainingExperience"
    },
    "Knowledge.csv": {
        "node_col": "Element Name",
        "scale_col": "Scale Name",
        "value_col": "Data Value",
        "relationship_prop_map": {"IM": "importance", "LV": "level"},
        "classification": "Knowledge"
    },
    "Skills.csv": {
        "node_col": "Element Name",
        "scale_col": "Scale Name",
        "value_col": "Data Value",
        "relationship_prop_map": {"IM": "importance", "LV": "level"},
        "classification": "Skill"
    },
    "Work Activities.csv": {
        "node_col": "Element Name",
        "scale_col": "Scale Name",
        "value_col": "Data Value",
        "relationship_prop_map": {"IM": "importance", "LV": "level"},
        "classification": "WorkActivity"
    },
    "Technology Skills.csv": {
        "node_col": "Example",
        "extra_props": ["Commodity Title", "Hot Technology", "In Demand"],
        "classification": "TechnologySkill"
    },
    "Tools Used.csv": {
        "node_col": "Example",
        "extra_props": ["Commodity Title"],
        "classification": "Tool"
    }
}

# -------------------- Neo4j Write Functions --------------------
def create_nodes_and_relationship(tx, job_soc, job_title, node_name, rel_props):
    job_key = f"{job_soc} | {job_title}"

    tx.run("""
        MERGE (j:Job {jobKey: $job_key})
        SET j.SOC = $job_soc,
            j.title = $job_title

        MERGE (s:Skill {name: $node_name})

        MERGE (j)-[r:REQUIRES]->(s)
        SET r += $rel_props
    """,
    job_key=job_key,
    job_soc=job_soc,
    job_title=job_title,
    node_name=node_name,
    rel_props=rel_props)


def assign_classification(tx, node_name, classification):
    tx.run("""
        MATCH (s:Skill {name: $node_name})
        SET s.classification =
            CASE
                WHEN s.classification IS NULL
                    THEN [$classification]
                WHEN $classification IN s.classification
                    THEN s.classification
                ELSE s.classification + $classification
            END
    """,
    node_name=node_name,
    classification=classification)

# -------------------- Import + Classification --------------------
for file_name, config in DATASETS.items():
    file_path = DATA_FOLDER / file_name

    if not file_path.exists():
        print(f"File not found: {file_name}, skipping...")
        continue

    print(f"Processing {file_name}...")
    df = pd.read_csv(file_path)

    with driver.session() as session:
        for _, row in df.iterrows():
            soc = str(row["O*NET-SOC Code"])
            title = str(row["Title"])
            node_name = str(row[config["node_col"]])

            rel_props = {}

            # Scale-based datasets
            if "scale_col" in config and "value_col" in config:
                scale = row[config["scale_col"]]
                value = row[config["value_col"]]

                prop_name = config.get("relationship_prop_map", {}).get(scale)
                if prop_name:
                    rel_props[prop_name] = value

            # Extra properties (Technology / Tools)
            if "extra_props" in config:
                for col in config["extra_props"]:
                    if col in row and pd.notna(row[col]):
                        rel_props[re.sub(r"\s+", "_", col)] = row[col]

            if rel_props:
                session.execute_write(
                    create_nodes_and_relationship,
                    soc,
                    title,
                    node_name,
                    rel_props
                )

            # Assign classification
            session.execute_write(
                assign_classification,
                node_name,
                config["classification"]
            )

print("✅ All datasets imported and classifications assigned successfully.")

driver.close()
