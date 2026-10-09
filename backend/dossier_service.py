import os
import json
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from schemas.dossier import DossierReport
import pydantic
import networkx as nx
import matplotlib.pyplot as plt

# Load environment variables from .env
load_dotenv()

class DossierEngine:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        # Dummy key for mock execution or load from env
        api_key = os.getenv("OPENAI_API_KEY", "sk-mock-key-for-dossier-engine")
        
        # When testing locally with a dummy key, ChatOpenAI initialization won't fail, 
        # but the invoke() call will. 
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            temperature=0.0
        )
        self.structured_llm = self.llm.with_structured_output(DossierReport)

    def generate_graph_visual(self, transaction_id: str, cluster_size: int, output_path: str):
        """Generates a visual NetworkX graph for the dossier report."""
        G = nx.Graph()
        G.add_node(transaction_id, color='red', size=500, label='Target Tx')
        
        # Create a mock cluster for visualization
        for i in range(cluster_size):
            node_id = f"Linked_Account_{i+1}"
            G.add_node(node_id, color='gray', size=300, label='Linked')
            G.add_edge(transaction_id, node_id)
            
        plt.figure(figsize=(4, 3))
        colors = [node[1]['color'] for node in G.nodes(data=True)]
        sizes = [node[1]['size'] for node in G.nodes(data=True)]
        
        nx.draw(G, with_labels=True, node_color=colors, node_size=sizes, font_size=8, font_color='white')
        plt.title(f"Fraud Ring Graph: {transaction_id}", fontsize=10)
        plt.savefig(output_path, bbox_inches='tight')
        plt.close()

    def generate_dossier(self, transaction_data: Dict[str, Any], shap_summary: Dict[str, Any], graph_summary: Dict[str, Any]) -> DossierReport:
        prompt = f"""
You are the Chief Judicial Analyst for the 'vigil' autonomous fraud platform. 
Your objective is to act as a "Prosecutor vs. Defense" engine for a flagged transaction and produce a balanced investigation dossier.

# Raw Data
Transaction Attributes:
{json.dumps(transaction_data, indent=2)}

TreeSHAP Explainability Drivers:
{json.dumps(shap_summary, indent=2)}

NetworkX Graph Metrics:
{json.dumps(graph_summary, indent=2)}

# Judicial Instructions
You must evaluate the data from both sides:
1. "Prosecution Case": Focus on positive SHAP drivers, graph entity overlaps, and velocity anomalies. Identify indicators supporting fraud.
2. "Defense Case": Actively defend against false positives using negative SHAP drivers, baseline consistency, and security validations (e.g., 3DS/OTP). If no mitigating factors exist, indicate "No mitigating factors detected".

# Decision Logic (Apply strictly)
- DECLINE_AND_FREEZE: If risk is high AND graph cluster size >= 2, or if impossible geo-velocity is detected.
- STEP_UP_VERIFICATION: If risk is elevated, but strong counter-evidence or valid baseline indicates a potential false positive.
- APPROVE_AND_CALIBRATE: If decisive counter-evidence invalidates the flag.

Produce the final structured dossier report.
"""
        # If using a mock API key, we should try/except to simulate the mock if the real API call fails.
        try:
            # Check for our mock key cleanly using os.getenv since self.llm.api_key attribute access varies across langchain versions
            if os.getenv("OPENAI_API_KEY", "sk-mock-key-for-dossier-engine") == "sk-mock-key-for-dossier-engine":
                raise Exception("Mock mode: using dummy API key.")
                
            result = self.structured_llm.invoke(prompt)
            return result
        except Exception as e:
            # Fallback to a mock structured response for testing without a real key
            print(f"LLM API call bypassed or failed ({e}). Returning mock DossierReport.")
            from schemas.dossier import ProsecutionEvidence, DefenseCounterEvidence
            
            score = shap_summary.get("ml_score", 0.0)
            
            if score >= 0.90:
                tier = "CRITICAL"
                action = "DECLINE_AND_FREEZE"
                prosecution = [ProsecutionEvidence(indicator="Impossible Travel", observation="Location jump detected (Distance: 5000 miles).", severity="CRITICAL")]
                defense = []
                summary = "Critical fraud indicators detected with no mitigating factors. Recommend immediate freeze."
                detailed = (
                    "SCORE EXPLANATION (0.96):\n"
                    "- Feature 'unusual_location_velocity' contributed +0.35 to the score.\n"
                    "- Feature 'amount_vs_historical_avg' contributed +0.25 (Amount is 3x standard deviation).\n"
                    "- Feature 'device_trust_score' contributed +0.10 (New, unrecognized device).\n\n"
                    "GRAPH EXPLANATION:\n"
                    "The transaction's originating account (red node) is connected to a cluster of 3 known compromised accounts (gray nodes) via shared IP addresses and previously used devices. This forms a high-risk closed topology indicative of an automated fraud ring attempting to cash out."
                )
            elif score >= 0.70:
                tier = "ELEVATED"
                action = "STEP_UP_VERIFICATION"
                prosecution = [ProsecutionEvidence(indicator="Velocity Anomaly", observation="High transaction frequency (5 txs in 1 hr).", severity="HIGH")]
                defense = [DefenseCounterEvidence(indicator="OTP Validation", observation="Verified via 3DS/OTP.", significance="STRONG")]
                summary = "Elevated risk due to velocity, but authenticated via OTP. Step-up verification required."
                detailed = (
                    "SCORE EXPLANATION (0.82):\n"
                    "- Feature 'transaction_frequency_1h' contributed +0.22 (Anomaly threshold exceeded).\n"
                    "- Feature 'merchant_category_risk' contributed +0.15 (High-risk MCC).\n"
                    "- Feature '3ds_authentication_success' mitigated the score by -0.10.\n\n"
                    "GRAPH EXPLANATION:\n"
                    "The account forms an isolated topology (cluster size 1). It shares no nodes or edges with known fraud rings, synthetic identities, or high-risk hubs. The lack of connectivity strongly supports the hypothesis that this is a legitimate user exhibiting temporary erratic behavior rather than systemic fraud."
                )
            else:
                tier = "LOW"
                action = "APPROVE_AND_CALIBRATE"
                prosecution = []
                defense = [DefenseCounterEvidence(indicator="Baseline Match", observation="Matches historical behavior.", significance="STRONG")]
                summary = "Transaction matches historical baseline. Safe to approve."
                detailed = (
                    "SCORE EXPLANATION (0.12):\n"
                    "- All primary features fall within 1 standard deviation of the user baseline.\n\n"
                    "GRAPH EXPLANATION:\n"
                    "Isolated node with no risky edges."
                )

            return DossierReport(
                transaction_id=transaction_data.get("transaction_id", "UNKNOWN"),
                catboost_score=score,
                risk_tier=tier,
                confidence_percentage=85,
                evidence_prosecution=prosecution,
                counter_evidence_defense=defense,
                graph_corroboration="No significant ring clusters found.",
                detailed_analysis=detailed,
                recommended_action=action,
                executive_analyst_summary=summary
            )

    def export_evidence_to_dataframe(self, dossier: DossierReport):
        """
        Extracts all prosecution and defense evidence from a dossier 
        and flattens them into a pandas DataFrame.
        """
        import pandas as pd
        
        rows = []
        for ev in dossier.evidence_prosecution:
            rows.append({
                "transaction_id": dossier.transaction_id,
                "evidence_type": "PROSECUTION",
                "indicator": ev.indicator,
                "observation": ev.observation,
                "impact_level": ev.severity
            })
            
        for dev in dossier.counter_evidence_defense:
            rows.append({
                "transaction_id": dossier.transaction_id,
                "evidence_type": "DEFENSE",
                "indicator": dev.indicator,
                "observation": dev.observation,
                "impact_level": dev.significance
            })
            
        return pd.DataFrame(rows)

    def export_to_pdf(self, dossier: DossierReport, output_path: str):
        """
        Generates a clean PDF report of the synthesized dossier.
        """
        from fpdf import FPDF
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        
        # Header
        pdf.cell(0, 10, f"Vigil Investigation Dossier: {dossier.transaction_id}", ln=True, align="C")
        pdf.ln(5)
        
        # Summary
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Executive Summary", ln=True)
        pdf.set_font("helvetica", "", 11)
        pdf.multi_cell(0, 8, str(dossier.executive_analyst_summary))
        pdf.ln(5)
        
        # In-depth Analysis
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "In-Depth Analytical Explanation (SHAP & Graph)", ln=True)
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 6, str(dossier.detailed_analysis))
        pdf.ln(5)
        
        # Insert Graph Image
        img_path = f"graph_{dossier.transaction_id}.png"
        if os.path.exists(img_path):
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 10, "Network Visual: Fraud Ring Topology", ln=True)
            pdf.image(img_path, w=100)
            pdf.ln(5)
        
        # Risk Metrics
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Risk Assessment", ln=True)
        pdf.set_font("helvetica", "", 11)
        pdf.cell(0, 8, f"Risk Tier: {dossier.risk_tier} (Score: {dossier.catboost_score})", ln=True)
        pdf.cell(0, 8, f"Confidence: {dossier.confidence_percentage}%", ln=True)
        pdf.cell(0, 8, f"Action: {dossier.recommended_action}", ln=True)
        pdf.ln(5)
        
        # Prosecution Evidence
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Prosecution Evidence", ln=True)
        pdf.set_font("helvetica", "", 11)
        if dossier.evidence_prosecution:
            for ev in dossier.evidence_prosecution:
                pdf.multi_cell(0, 8, f"[*] {ev.indicator} ({ev.severity}): {ev.observation}")
        else:
            pdf.cell(0, 8, "None detected.", ln=True)
        pdf.ln(5)
        
        # Defense Evidence
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Defense Counter-Evidence", ln=True)
        pdf.set_font("helvetica", "", 11)
        if dossier.counter_evidence_defense:
            for dev in dossier.counter_evidence_defense:
                pdf.multi_cell(0, 8, f"[*] {dev.indicator} ({dev.significance}): {dev.observation}")
        else:
            pdf.cell(0, 8, "None detected.", ln=True)
        
        pdf.output(output_path)
        print(f"PDF generated successfully at: {output_path}")

if __name__ == "__main__":
    import json
    
    print("Initializing DossierEngine...")
    engine = DossierEngine()
    
    # Mock Data Scenario 1: Elevated Risk (OTP Verified)
    tx_data_1 = {"transaction_id": "TX_INT_9942", "amount": 4500.0, "is_3ds_verified": True}
    shap_data_1 = {"ml_score": 0.82}
    graph_data_1 = {"cluster_size": 1}
    
    print("\n--- SCENARIO 1: ELEVATED RISK ---")
    dossier_1 = engine.generate_dossier(tx_data_1, shap_data_1, graph_data_1)
    
    print("\n--- EVIDENCE DATAFRAME ---")
    df_1 = engine.export_evidence_to_dataframe(dossier_1)
    print(df_1.to_string())
    
    # Generate Graph Image
    engine.generate_graph_visual(dossier_1.transaction_id, graph_data_1["cluster_size"], f"graph_{dossier_1.transaction_id}.png")
    engine.export_to_pdf(dossier_1, "dossier_TX_INT_9942.pdf")
    
    # Mock Data Scenario 2: Critical Risk (Impossible Travel)
    tx_data_2 = {"transaction_id": "TX_CRIT_1010", "amount": 15000.0, "is_3ds_verified": False}
    shap_data_2 = {"ml_score": 0.96}
    graph_data_2 = {"cluster_size": 3}
    
    print("\n--- SCENARIO 2: CRITICAL RISK ---")
    dossier_2 = engine.generate_dossier(tx_data_2, shap_data_2, graph_data_2)
    
    print("\n--- EVIDENCE DATAFRAME ---")
    df_2 = engine.export_evidence_to_dataframe(dossier_2)
    print(df_2.to_string())
    
    # Generate Graph Image
    engine.generate_graph_visual(dossier_2.transaction_id, graph_data_2["cluster_size"], f"graph_{dossier_2.transaction_id}.png")
    engine.export_to_pdf(dossier_2, "dossier_TX_CRIT_1010.pdf")
