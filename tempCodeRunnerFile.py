 except Exception as e:
            # Catch-all for API-level errors — quota, network, auth, etc.
            # We check the string because ClientError isn't easily importable
            error_str = str(e)    
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print("\n[Service Error] Gemini quota or rate limit reached.")
                print("Please wait a moment and try again, or check your API quota at https://ai.dev/rate-limit")
            else:
                print(f"\n[Service Error] Unexpected API error: {e}")
            continue