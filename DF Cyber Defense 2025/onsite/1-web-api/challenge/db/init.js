use(process.env.DB_NAME || "finovabank");

db.createUser({
  user: process.env.DB_USER || "appuser",
  pwd: process.env.DB_PASS || "bb4981aa2048c4e9e791ab6fe67e7e72",
  roles: [{ role: "read", db: process.env.DB_NAME || "finovabank" }]
});

db.statements.deleteMany({});

db.statements.insertMany([
  {
    accountNumber: "4532-1234-5678-9012",
    customerName: "John Smith",
    transactionType: "DEBIT",
    amount: 150.00,
    description: "Online Purchase - Electronics",
    merchantName: "Amazon",
    categories: ["shopping", "online"],
    transactionDate: new Date("2025-01-15T10:30:00Z"),
    status: "COMPLETED"
  },
  {
    accountNumber: "4532-1234-5678-9012", 
    customerName: "John Smith",
    transactionType: "CREDIT",
    amount: 2500.00,
    description: "Salary Deposit",
    merchantName: "TechCorp Inc",
    categories: ["salary", "income"],
    transactionDate: new Date("2025-01-01T09:00:00Z"),
    status: "COMPLETED"
  },
  {
    accountNumber: "5678-9012-3456-7890",
    customerName: "Sarah Johnson",
    transactionType: "DEBIT",
    amount: 85.50,
    description: "Grocery Shopping",
    merchantName: "Walmart",
    categories: ["groceries", "food"],
    transactionDate: new Date("2025-01-16T14:15:00Z"),
    status: "COMPLETED"
  },
  {
    accountNumber: "5678-9012-3456-7890",
    customerName: "Sarah Johnson",
    transactionType: "DEBIT",
    amount: 1200.00,
    description: "Monthly Rent Payment",
    merchantName: "Riverside Property Management",
    categories: ["rent", "housing"],
    transactionDate: new Date("2025-01-01T08:00:00Z"),
    status: "COMPLETED"
  },
  {
    accountNumber: "9012-3456-7890-1234",
    customerName: "Michael Brown",
    transactionType: "CREDIT",
    amount: 500.00,
    description: "Freelance Web Design Payment",
    merchantName: "Creative Design Studio",
    categories: ["freelance", "income"],
    transactionDate: new Date("2025-01-17T16:45:00Z"),
    status: "PENDING"
  },
  {
    accountNumber: "9012-3456-7890-1234",
    customerName: "Michael Brown",
    transactionType: "DEBIT",
    amount: 75.00,
    description: "Fuel Purchase",
    merchantName: "Shell Gas Station",
    categories: ["fuel", "transport"],
    transactionDate: new Date("2025-01-16T11:20:00Z"),
    status: "COMPLETED"
  },
  {
    accountNumber: "3456-7890-1234-5678",
    customerName: "Emily Davis",
    transactionType: "DEBIT",
    amount: 250.00,
    description: "Medical Consultation Fee",
    merchantName: "City General Hospital",
    categories: ["healthcare", "medical"],
    transactionDate: new Date("2025-01-14T13:30:00Z"),
    status: "COMPLETED"
  },
  {
    accountNumber: "3456-7890-1234-5678",
    customerName: "Emily Davis",
    transactionType: "CREDIT",
    amount: 3200.00,
    description: "Monthly Salary Deposit",
    merchantName: "HealthCare Solutions Corp",
    categories: ["salary", "income"],
    transactionDate: new Date("2025-01-01T09:15:00Z"),
    status: "COMPLETED"
  },
  {
    accountNumber: "4532-1234-5678-9012",
    customerName: "John Smith",
    transactionType: "DEBIT",
    amount: 45.99,
    description: "Coffee & Lunch",
    merchantName: "Starbucks",
    categories: ["food", "dining"],
    transactionDate: new Date("2025-01-18T12:15:00Z"),
    status: "COMPLETED"
  },
  {
    accountNumber: "5678-9012-3456-7890",
    customerName: "Sarah Johnson",
    transactionType: "CREDIT",
    amount: 150.00,
    description: "Cashback Reward",
    merchantName: "FinovaBank Rewards",
    categories: ["rewards", "cashback"],
    transactionDate: new Date("2025-01-19T10:00:00Z"),
    status: "COMPLETED"
  },
  {
    accountNumber: "9012-3456-7890-1234",
    customerName: "Michael Brown",
    transactionType: "DEBIT",
    amount: 299.99,
    description: "Software Subscription",
    merchantName: "Adobe Creative Cloud",
    categories: ["software", "subscription"],
    transactionDate: new Date("2025-01-20T09:30:00Z"),
    status: "COMPLETED"
  },
  {
    accountNumber: "3456-7890-1234-5678",
    customerName: "Emily Davis",
    transactionType: "DEBIT",
    amount: 120.00,
    description: "Pharmacy - Prescription",
    merchantName: "CVS Pharmacy",
    categories: ["healthcare", "pharmacy"],
    transactionDate: new Date("2025-01-21T14:45:00Z"),
    status: "COMPLETED"
  }
]);

print("FinovaBank statements collection seeded successfully!");
print("Total documents:", db.statements.countDocuments());