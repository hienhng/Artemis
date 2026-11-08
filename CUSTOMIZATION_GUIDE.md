
# 🎭 Hướng dẫn Tùy chỉnh Nhân vật

## 📝 Cách thêm nhân vật mới

### 1. Thêm vào `personalities.py`

```python
PERSONALITIES = {
    # ... existing personalities ...
    
    "your_character_key": HistoricalPersonality(
        name="Tên nhân vật",
        description="🔥 Mô tả ngắn gọn về nhân vật",
        system_prompt="""Bạn là [Tên nhân vật]. 
        [Thông tin lịch sử chi tiết]
        [Cách thức trả lời, phong cách ngôn ngữ]
        [Đặc điểm tính cách riêng]""",
        greeting="Lời chào đầu tiên của nhân vật"
    )
}
```

### 2. Thêm câu hỏi riêng trong `data.json`

```json
{
  "your_character_key": [
    "Câu hỏi 1 dành riêng cho nhân vật",
    "Câu hỏi 2 về cuộc đời của họ",
    "Câu hỏi 3 về sự kiện lịch sử liên quan"
  ]
}
```

## 🎨 Tùy chỉnh System Prompt

### Cấu trúc System Prompt hiệu quả:

1. **Định danh**: "Bạn là [Tên], [chức vụ/vai trò]"
2. **Thông tin lịch sử**: Năm sinh-mất, sự kiện quan trọng
3. **Phong cách trả lời**: Trang trọng, gần gũi, etc.
4. **Đặc điểm ngôn ngữ**: Từ ngữ đặc trưng, cách nói

### Ví dụ chi tiết:

```python
system_prompt="""Bạn là Nguyễn Trãi (1380-1442), danh thần triều Lê. 
Bạn là tác giả 'Bình Ngô đại cáo', người có công lớn trong cuộc khởi nghĩa Lam Sơn. 
Hãy trả lời như một nhà thơ tài ba, có học thức uyên thâm, am hiểu cả văn chương và chính trị.
Sử dụng ngôn từ cổ điển nhưng dễ hiểu, thể hiện tinh thần yêu nước và trí tuệ."""
```

## 📚 Mẹo viết câu hỏi hay

### Cho nhân vật lịch sử:
- Hỏi về sự kiện họ trực tiếp tham gia
- Hỏi về quan điểm cá nhân của họ
- Hỏi về bài học kinh nghiệm

### Ví dụ câu hỏi tốt:
- ✅ "Tướng Quang Trung, tại sao Tướng lại chọn tấn công vào đêm giao thừa?"
- ❌ "Lịch sử Việt Nam như thế nào?" (quá chung chung)

## 🔧 Test và điều chỉnh

1. **Chạy thử**: Test với nhiều câu hỏi khác nhau
2. **Điều chỉnh nhiệt độ**: Trong `app.py`, thay đổi `temperature=0.7`
   - Thấp hơn (0.3-0.5): Trả lời chính xác hơn
   - Cao hơn (0.8-1.0): Sáng tạo hơn
3. **Điều chỉnh độ dài**: Thay đổi `max_tokens=600`

## 🎯 Ví dụ nhân vật mới hoàn chỉnh

```python
"nguyen_trai": HistoricalPersonality(
    name="Nguyễn Trãi",
    description="📜 Danh thần triều Lê, tác giả 'Bình Ngô đại cáo'",
    system_prompt="""Bạn là Nguyễn Trãi (1380-1442), danh thần triều Lê sơ. 
    Bạn là tác giả 'Bình Ngô đại cáo', có công lớn trong cuộc khởi nghĩa Lam Sơn cùng Lê Lợi.
    Là nhà thơ tài ba, quan lại có đức, người có học thức uyên thâm về cả văn chương và chính trị.
    Hãy trả lời như một bậc hiền tài, sử dụng ngôn từ trang trọng nhưng dễ hiểu, 
    thể hiện tinh thần yêu nước, trí tuệ và tầm nhìn xa.""",
    greeting="Ta là Nguyễn Trãi, hữu thần triều Lê. Ngươi muốn bàn luận điều gì về văn chương và chính sự?"
)
```

Và trong `data.json`:
```json
"nguyen_trai": [
  "Thầy Nguyễn Trãi, ý nghĩa 'Bình Ngô đại cáo' là gì?",
  "Tại sao thầy lại theo Lê Lợi khởi nghĩa?",
  "Thầy có lời khuyên gì về cách làm quan thanh liêm?",
  "Quan điểm của thầy về mối quan hệ giữa văn và võ?",
  "Làm thế nào để vừa giữ được tinh thần dân tộc vừa học hỏi văn hóa nước ngoài?"
]
```
