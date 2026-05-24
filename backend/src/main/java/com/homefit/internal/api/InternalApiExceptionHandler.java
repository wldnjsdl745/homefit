package com.homefit.internal.api;

import com.homefit.internal.dto.ErrorResponse;
import com.homefit.internal.service.InvalidInternalApiRequestException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class InternalApiExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(InternalApiExceptionHandler.class);

    @ExceptionHandler(InvalidInternalApiRequestException.class)
    public ResponseEntity<ErrorResponse> handleInvalidRequest(InvalidInternalApiRequestException exception) {
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(new ErrorResponse(
                        "BE-REQ-001",
                        "Invalid internal API request.",
                        exception.getMessage()
                ));
    }

    @ExceptionHandler({
            MethodArgumentNotValidException.class,
            HttpMessageNotReadableException.class
    })
    public ResponseEntity<ErrorResponse> handleBadRequest(Exception exception) {
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(new ErrorResponse(
                        "BE-REQ-002",
                        "Invalid request body.",
                        "Request body is malformed or does not match the API schema."
                ));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception exception) {
        log.error("Unhandled internal API error", exception);
        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new ErrorResponse(
                        "BE-SYS-001",
                        "Internal backend error.",
                        "Backend failed while processing the request."
                ));
    }
}
