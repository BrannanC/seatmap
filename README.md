### Example JSON

Keys are `flight_info` and numbers (each number represents a row)

```json
{
  "flight_info": { "flight_no": "1179" },
  "1": {
    "class": "First",
    "layout": "AB EF",
    "seats": [
      {
        "seat_id": "1A",
        "class": "First",
        "available": false,
        "occupied": false,
        "seat_type": "Seat"
      },
      {
        "seat_id": "1B",
        "class": "First",
        "available": false,
        "occupied": false,
        "seat_type": "Seat"
      },
      {
        "seat_id": "1E",
        "class": "First",
        "available": false,
        "occupied": false,
        "seat_type": "Seat"
      },
      {
        "seat_id": "1F",
        "class": "First",
        "available": false,
        "occupied": false,
        "seat_type": "Seat"
      }
    ]
  }
}
```

### Example seat object

In retrospect maybe I should have been more object oriented about this `¯\_(ツ)_/¯`

```python
seat = {
    'seat_number': '1A',
    'seat_type': 'Seat',
    'fee': {'price': '22.00', 'currency': 'USD'}, #optional
    'cabin_class': 'Economy',
    'available': False,
    'occupied': True
}
```
