from notion.repo_books import fetch_cover_url, _clean_title_for_search

# Test with book title marks
title_with_marks = "《埃隆·马斯克传》"
title_without_marks = "埃隆·马斯克传"
author = "沃尔特·艾萨克森"

print(f"Original title: {title_with_marks}")
print(f"Cleaned title: {_clean_title_for_search(title_with_marks)}")
print("=" * 60)

print(f"\nTesting with marks: {title_with_marks}")
result1 = fetch_cover_url(_clean_title_for_search(title_with_marks), author)
print(f"Result: {result1 if result1 else 'None'}")

print(f"\nTesting without marks: {title_without_marks}")
result2 = fetch_cover_url(title_without_marks, author)
print(f"Result: {result2 if result2 else 'None'}")

print("=" * 60)