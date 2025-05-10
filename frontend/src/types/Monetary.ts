import { Currency } from "../services/AccountService";


interface Monetary {
  amount: number;
  currency: Currency;
}

class MonetaryValue {
  private amount: number;
  private currency: Currency;
  
  constructor(amount: number, currency: Currency) {
    this.amount = Number(amount.toFixed(2)); // Ensure 2 decimal places
    this.currency = currency;
  }
  
  format(): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: this.currency
    }).format(this.amount);
  }
  
  toJSON(): Monetary {
    return {
      amount: this.amount,
      currency: this.currency
    };
  }
}
