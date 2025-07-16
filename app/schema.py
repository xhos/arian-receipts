class Item:
	def __init__(self, name, price, qty):
		self.name = name
		self.price = price
		self.qty = qty


class Receipt:
	def __init__(self, merchant, date, total, items):
		self.merchant = merchant
		self.date = date
		self.total = total
		self.items = items
