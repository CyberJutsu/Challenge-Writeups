package org.finovabank;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.data.mongodb.repository.Query;

import java.util.List;

public interface StatementRepo extends MongoRepository<Statement, String> {

    @Query("{ 'customerName': { $regex: ?#{ \"?0\" }, $options: 'i' } }")
    List<Statement> findByCustomerName(String customerName);
    List<Statement> findByMerchantNameContainingIgnoreCase(String merchantName);
    List<Statement> findByTransactionDateContainingIgnoreCase(String transactionDate);
    List<Statement> findByTransactionType(String transactionType);
}


