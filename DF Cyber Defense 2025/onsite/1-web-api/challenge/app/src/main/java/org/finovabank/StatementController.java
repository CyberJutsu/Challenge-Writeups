package org.finovabank;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/statements")
public class StatementController {

    private final StatementRepo statementRepo;

    public StatementController(StatementRepo statementRepo) {
        this.statementRepo = statementRepo;
    }

    @GetMapping("/search")
    public List<Statement> search(
        @RequestParam(required = false) String customerName,
        @RequestParam(required = false) String merchantName,
        @RequestParam(required = false) String transactionDate,
        @RequestParam(required = false) String transactionType
    ) {
        List<Statement> results = statementRepo.findAll();
        
        if (customerName != null && !customerName.trim().isEmpty()) {
            results = statementRepo.findByCustomerName(customerName);
        }

        if (merchantName != null && !merchantName.trim().isEmpty()) {
            results = results.stream()
                .filter(s -> s.getMerchantName() != null && 
                        s.getMerchantName().toLowerCase().contains(merchantName.toLowerCase()))
                .collect(Collectors.toList());
        }
        
        if (transactionDate != null && !transactionDate.trim().isEmpty()) {
            results = results.stream()
                .filter(s -> s.getTransactionDate() != null && 
                        s.getTransactionDate().toString().toLowerCase().contains(transactionDate.toLowerCase()))
                .collect(Collectors.toList());
        }
        
        if (transactionType != null && !transactionType.trim().isEmpty()) {
            results = results.stream()
                .filter(s -> transactionType.equals(s.getTransactionType()))
                .collect(Collectors.toList());
        }
        
        return results;
    }

    @GetMapping("/healthz")
    public String healthz() {
        return "ok";
    }
    
    @GetMapping
    public List<Statement> getAllStatements() {
        return statementRepo.findAll();
    }
}


