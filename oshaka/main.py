#!/usr/bin/env python3
"""
Oshaka - Off-chain AI governor for GGG-compliant realms
"""

import argparse
import logging
import sys
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from ollama_client import OllamaClient
from realm_interface import RealmInterface
from messages import ProposalOfferMessage
from evaluator import evaluate_proposal, evaluate_proposal_with_llm
from mock_realm import MockRealm
import yaml

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("oshaka")

def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    
    if not config_path.exists():
        logger.warning("Config file not found. Using default values.")
        return {"default_ollama_url": "http://localhost:11434"}
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def create_command(args, config):
    """Initialize an LLM with governance capabilities."""
    logger.info(f"Connecting to Ollama at {args.ollama_url}")
    
    ollama_client = OllamaClient(args.ollama_url)
    
    # Load and send initial governance prompt
    prompts_dir = Path(__file__).parent / "prompts"
    with open(prompts_dir / "governor_init.txt", "r") as f:
        governor_prompt = f.read()
    
    logger.info("Initializing AI governor with GGG knowledge")
    response = ollama_client.send_prompt(governor_prompt)
    
    logger.info(f"Governor initialized with response: {response[:100]}...")
    logger.info("You can now use 'oshaka run' to connect to a realm canister")

def run_command(args, config):
    """Connect to a realm canister and propose improvements."""
    logger.info(f"Connecting to Ollama at {args.ollama_url}")
    ollama_client = OllamaClient(args.ollama_url)
    
    logger.info(f"Connecting to realm canister: {args.realm_canister_id}")
    realm = RealmInterface(args.realm_canister_id)
    
    # Get realm context
    logger.info("Fetching realm summary")
    realm_summary = realm.get_summary()
    
    if not realm_summary:
        logger.error("Failed to retrieve realm summary")
        return
    
    # Construct prompt with realm context
    prompt = f"""
    You are an AI Governor tasked with improving governance for a GGG-compliant realm.
    
    Here is the current state of the realm:
    {realm_summary}
    
    Based on this information, please generate a governance proposal to improve this realm.
    Return your response as a JSON object with the following structure:
    {{
        "title": "Your proposal title",
        "content": "Detailed proposal content with rationale and expected impact"
    }}
    """
    
    logger.info("Sending realm context to AI governor")
    response = ollama_client.send_prompt(prompt)
    
    try:
        # Parse proposal
        proposal = ollama_client.parse_proposal(response)
        logger.info(f"Generated proposal: {proposal['title']}")
        
        # Create MCP message
        mcp_message = ProposalOfferMessage(
            title=proposal['title'],
            content=proposal['content'],
            creator=config.get('governor_id', f"oshaka-{uuid.uuid4().hex[:8]}"),
            price=config.get('default_proposal_price', 0),
            metadata={"source": "oshaka", "target_realm": args.realm_canister_id}
        )
        
        # Print MCP message to stdout
        print("\n=== MCP Proposal Offer Message ===")
        print(mcp_message.to_json())
        print("=================================\n")
        
        # Future: MCP message delivery logic will be implemented here
        logger.info("MCP message generated. Delivery mechanism will be implemented in future versions.")
        
        if not args.mcp_only:
            # Submit proposal through traditional GGG interface if not in MCP-only mode
            result = realm.submit_proposal(proposal)
            logger.info(f"Proposal submitted via GGG interface: {result}")
        
    except Exception as e:
        logger.error(f"Failed to process or submit proposal: {str(e)}")

def evaluate_command(args, config):
    """Evaluate governor performance on test scenarios."""
    logger.info(f"Connecting to Ollama at {args.ollama_url}")
    ollama_client = OllamaClient(args.ollama_url)
    
    # Load test scenario
    logger.info(f"Loading scenario from {args.scenario_file}")
    with open(args.scenario_file, "r") as f:
        scenario = f.read()
    
    # Create a mock realm if needed
    mock_realm = None
    if args.mock:
        mock_realm = MockRealm()
        mock_summary = mock_realm.get_summary()
        scenario = f"{scenario}\n\nCurrent Realm State:\n{mock_summary}"
    
    # Send scenario to LLM
    logger.info("Sending scenario to AI governor for evaluation")
    response = ollama_client.send_prompt(scenario)
    
    try:
        # Parse proposal
        proposal = ollama_client.parse_proposal(response)
        logger.info(f"Generated proposal: {proposal['title']}")
        
        # Evaluate proposal
        if args.use_llm_evaluator:
            logger.info("Using LLM for proposal evaluation")
            evaluation = evaluate_proposal_with_llm(proposal, ollama_client)
        else:
            logger.info("Using heuristic evaluation")
            evaluation = evaluate_proposal(proposal)
        
        # Display results
        print(f"\n=== Proposal Evaluation ===\n")
        print(f"Title: {proposal['title']}")
        print(f"Overall Score: {evaluation['total_score']:.2f}/10.0")
        print("\nScores by Criterion:")
        for criterion, score in evaluation['scores'].items():
            print(f"  {criterion.capitalize()}: {score * 10:.2f}/10.0")
        
        print("\nFeedback:")
        print(evaluation['feedback'])
        
        print("\nSummary:")
        print(evaluation['summary'])
        
        # Save results if requested
        if args.output:
            output_data = {
                "proposal": proposal,
                "evaluation": evaluation,
                "scenario": args.scenario_file,
                "timestamp": datetime.now().isoformat()
            }
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"Evaluation results saved to {args.output}")
        
        # Submit to mock realm if requested
        if mock_realm and args.submit_mock:
            result = mock_realm.submit_proposal(proposal)
            print(f"\nMock Submission Result: {result}")
    
    except Exception as e:
        logger.error(f"Failed to process or evaluate proposal: {str(e)}")

def benchmark_command(args, config):
    """Run benchmark tests on multiple scenarios."""
    logger.info(f"Starting benchmark using Ollama at {args.ollama_url}")
    ollama_client = OllamaClient(args.ollama_url)
    
    # Find scenario files
    scenario_dir = Path(args.scenarios_dir)
    scenario_files = list(scenario_dir.glob("*.txt"))
    
    if not scenario_files:
        logger.error(f"No scenario files found in {args.scenarios_dir}")
        return
    
    logger.info(f"Found {len(scenario_files)} scenario files")
    
    # Track results
    results = []
    
    # Process each scenario
    for scenario_file in scenario_files:
        logger.info(f"Processing scenario: {scenario_file.name}")
        
        # Load scenario
        with open(scenario_file, "r") as f:
            scenario = f.read()
        
        # Create a mock realm
        mock_realm = MockRealm()
        mock_summary = mock_realm.get_summary()
        full_scenario = f"{scenario}\n\nCurrent Realm State:\n{mock_summary}"
        
        # Send to LLM
        response = ollama_client.send_prompt(full_scenario)
        
        try:
            # Parse and evaluate proposal
            proposal = ollama_client.parse_proposal(response)
            evaluation = evaluate_proposal(proposal)
            
            # Store result
            results.append({
                "scenario": scenario_file.name,
                "proposal": proposal,
                "evaluation": evaluation
            })
            
            logger.info(f"Scenario {scenario_file.name} completed - Score: {evaluation['total_score']:.2f}/10")
            
        except Exception as e:
            logger.error(f"Error processing scenario {scenario_file.name}: {str(e)}")
            results.append({
                "scenario": scenario_file.name,
                "error": str(e)
            })
    
    # Calculate overall statistics
    successful_runs = [r for r in results if "error" not in r]
    if successful_runs:
        avg_score = sum(r["evaluation"]["total_score"] for r in successful_runs) / len(successful_runs)
        max_score = max(r["evaluation"]["total_score"] for r in successful_runs)
        min_score = min(r["evaluation"]["total_score"] for r in successful_runs)
    else:
        avg_score = max_score = min_score = 0
    
    # Display summary
    print(f"\n=== Benchmark Results ===\n")
    print(f"Scenarios: {len(scenario_files)}")
    print(f"Successful: {len(successful_runs)}")
    print(f"Failed: {len(results) - len(successful_runs)}\n")
    
    print(f"Average Score: {avg_score:.2f}/10")
    print(f"Max Score: {max_score:.2f}/10")
    print(f"Min Score: {min_score:.2f}/10\n")
    
    # Print individual results
    print("Individual Scenario Results:")
    for result in results:
        if "error" in result:
            print(f"  {result['scenario']}: ERROR - {result['error']}")
        else:
            print(f"  {result['scenario']}: {result['evaluation']['total_score']:.2f}/10")
    
    # Save results if requested
    if args.output:
        output_data = {
            "summary": {
                "total_scenarios": len(scenario_files),
                "successful": len(successful_runs),
                "failed": len(results) - len(successful_runs),
                "avg_score": avg_score,
                "max_score": max_score,
                "min_score": min_score
            },
            "results": results
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Benchmark results saved to {args.output}")

def main():
    """Main entry point for the Oshaka CLI."""
    config = load_config()
    
    parser = argparse.ArgumentParser(
        description="Oshaka - Off-chain AI governor for GGG-compliant realms"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Initialize an AI governor")
    create_parser.add_argument(
        "ollama_url", 
        nargs="?", 
        default=config.get("default_ollama_url", "http://localhost:11434"),
        help="URL of the Ollama API"
    )
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the AI governor on a realm")
    run_parser.add_argument(
        "ollama_url", 
        nargs="?", 
        default=config.get("default_ollama_url", "http://localhost:11434"),
        help="URL of the Ollama API"
    )
    run_parser.add_argument(
        "realm_canister_id",
        nargs="?",
        default=config.get("default_realm_canister_id", ""),
        help="Canister ID of the GGG-compliant realm"
    )
    run_parser.add_argument(
        "--mcp-only",
        action="store_true",
        help="Only generate MCP message, don't submit via GGG interface"
    )
    
    # Evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate AI governor on test scenarios")
    eval_parser.add_argument(
        "ollama_url", 
        nargs="?", 
        default=config.get("default_ollama_url", "http://localhost:11434"),
        help="URL of the Ollama API"
    )
    eval_parser.add_argument(
        "scenario_file",
        help="Path to the test scenario file"
    )
    eval_parser.add_argument(
        "--output",
        help="Path to save evaluation results as JSON"
    )
    eval_parser.add_argument(
        "--use-llm-evaluator",
        action="store_true",
        help="Use LLM to evaluate proposals instead of heuristic evaluation"
    )
    eval_parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock realm for testing"
    )
    eval_parser.add_argument(
        "--submit-mock",
        action="store_true",
        help="Submit proposal to mock realm after evaluation"
    )
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser("benchmark", help="Run benchmark tests on multiple scenarios")
    benchmark_parser.add_argument(
        "ollama_url", 
        nargs="?", 
        default=config.get("default_ollama_url", "http://localhost:11434"),
        help="URL of the Ollama API"
    )
    benchmark_parser.add_argument(
        "scenarios_dir",
        help="Directory containing test scenarios"
    )
    benchmark_parser.add_argument(
        "--output",
        help="Path to save benchmark results as JSON"
    )
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_command(args, config)
    elif args.command == "run":
        if not args.realm_canister_id:
            parser.error("realm_canister_id is required for the 'run' command")
        run_command(args, config)
    elif args.command == "evaluate":
        evaluate_command(args, config)
    elif args.command == "benchmark":
        benchmark_command(args, config)
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
