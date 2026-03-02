#!/usr/bin/env python3
"""Test script for new SalesLens features with mock data.

Run this after starting the backend to test:
1. Correlation Analysis
2. Lead-Level Rollup
3. Data Capture Questions
4. Weekly Reports

Usage:
    python test_new_features.py
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "admin@test.com"
TEST_PASSWORD = "test123"

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.ENDC}\n")


def print_success(text: str):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_json(data: Dict[Any, Any], title: str = ""):
    if title:
        print(f"{Colors.OKBLUE}{title}:{Colors.ENDC}")
    print(json.dumps(data, indent=2))


class SalesLensTester:
    def __init__(self):
        self.token = None
        self.tenant_id = None
        self.user_id = None

    def authenticate(self) -> bool:
        """Login and get auth token."""
        print_header("1. AUTHENTICATION")

        try:
            # Try to login first
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.tenant_id = data["tenant_id"]
                self.user_id = data["user_id"]
                print_success(f"Logged in as {TEST_EMAIL}")
                print_info(f"Tenant ID: {self.tenant_id}")
                return True
            else:
                print_error(f"Login failed: {response.json()}")
                return False

        except Exception as e:
            print_error(f"Authentication error: {e}")
            return False

    def get_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {self.token}"}

    def test_correlation_analysis(self):
        """Test correlation analysis endpoint."""
        print_header("2. CORRELATION ANALYSIS")

        try:
            response = requests.get(
                f"{BASE_URL}/analytics/correlations",
                headers=self.get_headers(),
                params={"period_days": 30, "min_sample_size": 5}
            )

            if response.status_code == 200:
                data = response.json()
                print_success("Correlation analysis retrieved successfully")

                metadata = data.get("metadata", {})
                print_info(f"Calls analyzed: {metadata.get('total_calls_analyzed', 0)}")
                print_info(f"Hot leads: {metadata.get('hot_leads_count', 0)}")
                print_info(f"Cold leads: {metadata.get('cold_leads_count', 0)}")

                # Top parameters
                top_params = data.get("parameter_correlations", {}).get("top_drivers", [])
                if top_params:
                    print("\n" + Colors.OKBLUE + "Top Performing Parameters:" + Colors.ENDC)
                    for param in top_params[:3]:
                        print(f"  • {param['parameter_name']}: "
                              f"correlation={param['correlation_strength']:.2f}, "
                              f"impact={param['impact_category']}")

                # Recommendations
                recs = data.get("recommendations", [])
                if recs:
                    print("\n" + Colors.OKBLUE + "Recommendations:" + Colors.ENDC)
                    for rec in recs:
                        print(f"  → {rec}")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print_error(f"Error: {e}")
            return False

    def test_lead_rollup(self):
        """Test lead-level data rollup."""
        print_header("3. LEAD-LEVEL ROLLUP")

        try:
            # List all leads
            response = requests.get(
                f"{BASE_URL}/leads",
                headers=self.get_headers(),
                params={"page": 1, "page_size": 10}
            )

            if response.status_code == 200:
                leads = response.json()
                print_success(f"Retrieved {len(leads)} leads")

                if leads:
                    # Show first lead summary
                    lead = leads[0]
                    print_info(f"\nSample Lead: {lead.get('lead_name', 'Unknown')}")
                    print(f"  • Lead ID: {lead.get('lead_id')}")
                    print(f"  • Total Calls: {lead.get('total_calls')}")
                    print(f"  • Avg Quality: {lead.get('avg_quality_score')}")
                    print(f"  • Classification: {lead.get('latest_intent_classification')}")
                    print(f"  • Quality Trend: {lead.get('quality_trend')}")
                    print(f"  • Follow-up Urgency: {lead.get('follow_up_urgency')}")

                    # Get detailed view
                    lead_id = lead.get('lead_id')
                    detail_response = requests.get(
                        f"{BASE_URL}/leads/{lead_id}",
                        headers=self.get_headers()
                    )

                    if detail_response.status_code == 200:
                        detail = detail_response.json()
                        print("\n" + Colors.OKBLUE + "Lead Details:" + Colors.ENDC)

                        if detail.get('top_objections'):
                            print(f"  • Top Objections: {', '.join(detail['top_objections'][:3])}")

                        if detail.get('key_pain_points'):
                            print(f"  • Pain Points: {', '.join(detail['key_pain_points'][:3])}")

                        if detail.get('competitors_mentioned'):
                            print(f"  • Competitors: {', '.join(detail['competitors_mentioned'])}")

                        bant = detail.get('bant', {})
                        print(f"  • BANT Scores: B={bant.get('budget_score')}, "
                              f"A={bant.get('authority_score')}, "
                              f"N={bant.get('need_score')}, "
                              f"T={bant.get('timeline_score')}")
                else:
                    print_info("No leads found - upload some calls first")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print_error(f"Error: {e}")
            return False

    def test_data_capture_questions(self):
        """Test data capture questions CRUD."""
        print_header("4. DATA CAPTURE QUESTIONS")

        try:
            # List existing questions
            response = requests.get(
                f"{BASE_URL}/data-capture-questions",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                questions = response.json()
                print_success(f"Retrieved {len(questions)} data capture questions")

                for q in questions:
                    print(f"\n  • {q['question']}")
                    print(f"    Field: {q['field_name']}, Type: {q['expected_type']}")

                # Create a sample question
                print("\n" + Colors.OKCYAN + "Creating sample question..." + Colors.ENDC)
                new_question = {
                    "question": "Does the customer have a quote from a competitor?",
                    "field_name": "has_competitor_quote",
                    "expected_type": "boolean",
                    "description": "Check if customer mentioned having competitive quotes",
                    "category": "competitive",
                    "display_order": len(questions)
                }

                create_response = requests.post(
                    f"{BASE_URL}/data-capture-questions",
                    headers=self.get_headers(),
                    json=new_question
                )

                if create_response.status_code == 201:
                    created = create_response.json()
                    print_success(f"Created question: {created['field_name']}")
                    return True
                elif create_response.status_code == 400:
                    print_info("Question may already exist or limit reached (max 10 per tenant)")
                    return True
                else:
                    print_error(f"Failed to create: {create_response.text}")
                    return False

            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print_error(f"Error: {e}")
            return False

    def test_weekly_reports(self):
        """Test weekly reports generation and retrieval."""
        print_header("5. WEEKLY REPORTS")

        try:
            # List existing reports
            response = requests.get(
                f"{BASE_URL}/reports/weekly",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                reports = response.json()
                print_success(f"Retrieved {len(reports)} weekly reports")

                if reports:
                    report = reports[0]
                    print_info(f"\nLatest Report:")
                    print(f"  • Week: {report.get('week_start')} to {report.get('week_end')}")
                    print(f"  • Status: {report.get('status')}")

                    # Get detailed report
                    report_id = report.get('id')
                    detail_response = requests.get(
                        f"{BASE_URL}/reports/weekly/{report_id}",
                        headers=self.get_headers()
                    )

                    if detail_response.status_code == 200:
                        detail = detail_response.json()
                        report_data = detail.get('report_data', {})
                        summary = report_data.get('summary', {})

                        print("\n" + Colors.OKBLUE + "Report Summary:" + Colors.ENDC)
                        print(f"  • Total Calls: {summary.get('total_calls')}")
                        print(f"  • Avg Quality: {summary.get('avg_quality_score')}")
                        print(f"  • Hot Leads: {summary.get('hot_leads_count')}")
                else:
                    print_info("No reports found - generate one first")

                    # Try to generate a report
                    print("\n" + Colors.OKCYAN + "Generating sample report..." + Colors.ENDC)
                    week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

                    gen_response = requests.post(
                        f"{BASE_URL}/reports/weekly",
                        headers=self.get_headers(),
                        json={"week_start": week_start}
                    )

                    if gen_response.status_code == 201:
                        print_success("Report generation started")
                        print_info("Check /reports page in the dashboard for results")
                    else:
                        print_info(f"Could not generate: {gen_response.text}")

                return True
            else:
                print_error(f"Failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print_error(f"Error: {e}")
            return False

    def test_analytics_endpoint(self):
        """Test existing analytics to show data is flowing."""
        print_header("6. ANALYTICS VERIFICATION")

        try:
            response = requests.get(
                f"{BASE_URL}/analytics/team",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                stats = data.get('stats', {})

                print_success("Analytics data retrieved")
                print_info(f"Calls today: {stats.get('calls_today', 0)}")
                print_info(f"Avg quality score: {stats.get('avg_quality_score', 0)}")
                print_info(f"Hot leads count: {stats.get('hot_leads_count', 0)}")

                return True
            else:
                print_error(f"Failed: {response.status_code}")
                return False

        except Exception as e:
            print_error(f"Error: {e}")
            return False

    def run_all_tests(self):
        """Run all feature tests."""
        print(f"\n{Colors.BOLD}SalesLens Feature Testing{Colors.ENDC}")
        print(f"{Colors.BOLD}Testing new features with live backend{Colors.ENDC}\n")

        results = []

        # Authentication
        if not self.authenticate():
            print_error("\n❌ Authentication failed - check backend is running")
            return

        # Run all tests
        results.append(("Correlation Analysis", self.test_correlation_analysis()))
        results.append(("Lead Rollup", self.test_lead_rollup()))
        results.append(("Data Capture Questions", self.test_data_capture_questions()))
        results.append(("Weekly Reports", self.test_weekly_reports()))
        results.append(("Analytics", self.test_analytics_endpoint()))

        # Summary
        print_header("TEST SUMMARY")
        passed = sum(1 for _, result in results if result)
        total = len(results)

        for name, result in results:
            status = "✓" if result else "✗"
            color = Colors.OKGREEN if result else Colors.FAIL
            print(f"{color}{status} {name}{Colors.ENDC}")

        print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.ENDC}")

        if passed == total:
            print(f"\n{Colors.OKGREEN}🎉 All features working correctly!{Colors.ENDC}")
        else:
            print(f"\n{Colors.WARNING}⚠️  Some tests failed - check backend logs{Colors.ENDC}")


if __name__ == "__main__":
    tester = SalesLensTester()
    tester.run_all_tests()
